// Top-level build file. Shared plugin versions declared in gradle/libs.versions.toml.
plugins {
    // Kotlin support is built into AGP 9.0+; the kotlin-android plugin is intentionally omitted.
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.ksp) apply false
}
