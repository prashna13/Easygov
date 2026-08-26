plugins {
    alias(libs.plugins.android.application)
}

// Admin-configured backend URL, baked into the APK at build time so users never
// change it in the app. Override per build: ./gradlew :app:assembleDebug -Peasygov.baseUrl=http://192.168.1.72:8000/
val easygovBaseUrl: String =
    (project.findProperty("easygov.baseUrl") as? String)?.trim()?.takeIf { it.isNotEmpty() }
        ?: "http://10.0.2.2:8000/"

android {
    namespace = "com.example.easygov"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.example.easygov"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "BASE_URL", "\"$easygovBaseUrl\"")
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.swiperefreshlayout)
    implementation(libs.androidx.security.crypto)
    implementation(libs.androidx.core.ktx)
    implementation(libs.material)
    implementation("com.google.android.material:material:1.12.0")

    // Google Sign-In ("Continue with Google")
    implementation(libs.play.services.auth)
    // Networking & JSON Parsing
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")

    // Markdown text rendering
    implementation("io.noties.markwon:core:4.6.2")
testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.rules)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
}
