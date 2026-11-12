# kotlinx.serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class **$$serializer { *; }
-keepclasseswithmembers class com.miniagent.app.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.miniagent.app.**$$serializer { *; }
-keep @kotlinx.serialization.Serializable class com.miniagent.app.** { *; }

# Retrofit / OkHttp
-keepattributes Signature, Exceptions
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class retrofit2.** { *; }
