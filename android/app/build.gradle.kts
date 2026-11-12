import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    // Kotlin support is built into AGP 9.0+, so the kotlin-android plugin is not applied.
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

android {
    namespace = "com.miniagent.app"
    // Some AndroidX 2026.x artifacts require compiling against API 37; targetSdk stays at 36.
    compileSdk = 37

    defaultConfig {
        applicationId = "com.miniagent.app"
        minSdk = 26
        targetSdk = 36

        versionCode = 1
        versionName = "1.0.0"

        // ------------------------------------------------------------------
        // Backend API base URL. This is the ONLY place to change it for a build.
        // It can also be overridden at runtime in the app's 个人中心 -> 服务环境设置.
        //
        //   Android emulator  -> http://10.0.2.2:8000/api/v1   (host machine's localhost)
        //   Physical device   -> http://<your-LAN-ip>:8000/api/v1
        //   Production         -> https://your-domain.com/api/v1
        // ------------------------------------------------------------------
        buildConfigField(
            "String",
            "DEFAULT_BASE_URL",
            "\"http://10.0.2.2:8000/api/v1\"",
        )
    }

    buildTypes {
        debug {
            // Cleartext HTTP to localhost is allowed via network_security_config.xml
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)
    debugImplementation(libs.androidx.ui.tooling)

    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization.converter)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)

    implementation(libs.androidx.datastore.preferences)
    implementation(libs.coil.compose)
    implementation(libs.compose.markdown)
}
