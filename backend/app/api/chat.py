import anyio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.agent.runtime import ChatRuntime, sse_format
from app.core.database import get_db
from app.core.exceptions import NotFound
from app.core.permissions import get_current_user
from app.core.response import ok
from app.models import Conversation, Message, User
from app.schemas.chat import ChatIn, StopIn
from app.utils.cancel import request_cancel

router = APIRouter(prefix="/chat", tags=["对话"])


def _runtime(body: ChatIn, user: User) -> ChatRuntime:
    return ChatRuntime(user_id=user.id, agent_id=body.agent_id, conversation_id=body.conversation_id,
                       content=body.content, attachment_ids=body.attachment_ids, regenerate=body.regenerate)


@router.post("/completions", summary="非流式对话")
def completions(body: ChatIn, user: User = Depends(get_current_user)):
    rt = _runtime(body, user)
    try:
        rt.prepare()
        return ok(rt.run_blocking())
    finally:
        rt.close()


@router.post("/stream", summary="流式对话 (Server-Sent Events)",
             description="事件: meta / citations / tool / delta / done / error。客户端断开即视为取消，已生成内容保存为 interrupted。")
async def stream(body: ChatIn, request: Request, user: User = Depends(get_current_user)):
    rt = _runtime(body, user)
    try:
        await run_in_threadpool(rt.prepare)  # validation errors -> normal JSON error response
    except Exception:
        await run_in_threadpool(rt.close)
        raise
    gen = rt.iter_events()
    sentinel = object()

    async def event_source():
        finished = False
        try:
            yield ": connected\n\n"
            while True:
                event = await run_in_threadpool(next, gen, sentinel)
                if event is sentinel:
                    finished = True
                    break
                yield sse_format(event)
                if await request.is_disconnected():
                    break
        finally:
            with anyio.CancelScope(shield=True):
                if not finished:
                    await run_in_threadpool(gen.close)  # -> GeneratorExit -> saved as interrupted
                await run_in_threadpool(rt.close)

    return StreamingResponse(event_source(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


@router.post("/stop", summary="停止生成")
def stop(body: StopIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(Message, body.message_id)
    conv = db.get(Conversation, m.conversation_id) if m else None
    if m is None or conv is None or conv.user_id != user.id:
        raise NotFound("消息不存在")
    if m.status == "streaming":
        request_cancel(m.id)
    return ok({"message_id": m.id})
