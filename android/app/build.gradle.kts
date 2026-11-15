plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Version comes from the VERSION file at the repo root (e.g. 0.3.0).
val appVersion: String = (System.getenv("APP_VERSION")
    ?: rootProject.file("../VERSION").takeIf { it.exists() }?.readText()
    ?: "0.0.1").trim()
val parts = appVersion.split(".").map { it.toIntOrNull() ?: 0 } + listOf(0, 0, 0)
val appVersionCode = parts[0] * 10000 + parts[1] * 100 + parts[2]

val releaseKeystore = rootProject.file("release.jks")

android {
    namespace = "com.stellarhub.hubconnects"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.stellarhub.hubconnects"
        minSdk = 26
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersion
    }

    signingConfigs {
        create("release") {
            if (releaseKeystore.exists()) {
                storeFile = releaseKeystore
                storePassword = System.getenv("KEYSTORE_PASSWORD")
                keyAlias = "hubconnects"
                keyPassword = System.getenv("KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (releaseKeystore.exists()) signingConfigs.getByName("release")
                            else signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
