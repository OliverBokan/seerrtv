package ca.devmesh.seerrtv.baselineprofile

import androidx.benchmark.macro.MacrobenchmarkScope
import androidx.benchmark.macro.junit4.BaselineProfileRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Records the classes and methods SeerrTV touches at startup and in its main journeys, so they
 * can be compiled ahead of time instead of interpreted on first use.
 *
 * Why this exists: Play vitals captured an ANR whose main thread was Runnable inside
 * `WindowInsetsRulers.<clinit>`, reached from `AndroidComposeView.<init>` during the very first
 * `setContent`, with a concurrent GC running alongside it. That is a cold start grinding through
 * class loading and verification with nothing precompiled. A baseline profile targets exactly
 * that window, and the journeys extend it to the screens people use next.
 *
 * Needs a device **signed in to a Seerr server** with content on the home screen; otherwise the
 * run stops at the setup flow or the loading placeholders and the profile misses the real
 * screens. (The 2026-09 profile was recorded that way: it held `MediaCardPlaceholder` but no
 * media card, carousel, details, browse or search code.)
 *
 * Run with:  ANDROID_SERIAL=emulator-5554 ./gradlew :tv:generateBaselineProfile
 * The result lands in tv/src/main/generated/baselineProfiles/ and is meant to be committed.
 * Gradle uninstalls the app after the run, which signs the device out.
 */
@RunWith(AndroidJUnit4::class)
class StartupBaselineProfileGenerator {

    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    /**
     * Startup only, up to the first media posters on the home screen. Also emitted as the
     * startup profile, which lays out the dex so startup classes sit together and fault in with
     * fewer reads; that matters on the slow eMMC of cheap TV boxes. The journeys below are kept
     * out of it so they don't dilute that layout.
     */
    @Test
    fun startup() {
        baselineProfileRule.collect(
            packageName = TARGET_PACKAGE,
            includeInStartupProfile = true,
        ) {
            pressHome()
            startActivityAndWait()
            waitForHomeContent()
        }
    }

    /**
     * The main journeys after startup: scrolling the home rows, opening a title's details and
     * scrolling to its cast and similar titles, and browsing Movies. Each journey starts from a
     * fresh launch (killProcess saves the profile and resets focus to the first card), so no
     * journey depends on where the previous one left focus, and no Back press can walk out of
     * the app. Only D-pad input, so nothing is requested or changed on the server.
     */
    @Test
    fun journeys() {
        baselineProfileRule.collect(
            packageName = TARGET_PACKAGE,
            includeInStartupProfile = false,
        ) {
            // Home rows: along the first row, down through the rows and along again
            launchToHome()
            repeat(8) { press { device.pressDPadRight() } }
            repeat(3) { press { device.pressDPadDown() } }
            repeat(6) { press { device.pressDPadRight() } }
            repeat(2) { press { device.pressDPadDown() } }

            // Details of the first card, scrolled down to cast and similar titles
            relaunchToHome()
            press(SCREEN_SETTLE_MS) { device.pressDPadCenter() }
            repeat(6) { press { device.pressDPadDown() } }
            repeat(4) { press { device.pressDPadRight() } }

            // Movies browse grid, from the top bar (Up reaches Search, Left moves to Movies)
            relaunchToHome()
            press { device.pressDPadUp() }
            press { device.pressDPadLeft() }
            press(SCREEN_SETTLE_MS) { device.pressDPadCenter() }
            repeat(4) { press { device.pressDPadRight() } }
            repeat(3) { press { device.pressDPadDown() } }
        }
    }

    private fun MacrobenchmarkScope.launchToHome() {
        pressHome()
        startActivityAndWait()
        waitForHomeContent()
    }

    private fun MacrobenchmarkScope.relaunchToHome() {
        killProcess()
        launchToHome()
    }

    /** Waits until real media posters are on screen, not the splash or the loading placeholders. */
    private fun MacrobenchmarkScope.waitForHomeContent() {
        device.wait(Until.hasObject(By.desc(MEDIA_POSTER_DESCRIPTION)), HOME_CONTENT_TIMEOUT_MS)
        device.waitForIdle(INTERACTION_IDLE_TIMEOUT_MS)
    }

    private inline fun MacrobenchmarkScope.press(
        settleMs: Long = INTERACTION_IDLE_TIMEOUT_MS,
        action: MacrobenchmarkScope.() -> Unit
    ) {
        action()
        device.waitForIdle(settleMs)
    }

    private companion object {
        /** The `play`/`app` variant's applicationId; see missingDimensionStrategy in build.gradle.kts. */
        const val TARGET_PACKAGE = "ca.devmesh.seerrtv"

        /** Content description of every media poster (`common_mediaPoster`, English). */
        const val MEDIA_POSTER_DESCRIPTION = "Media Poster"

        /** Generous: the splash may be waiting on a Seerr instance over the network. */
        const val HOME_CONTENT_TIMEOUT_MS = 20_000L
        const val INTERACTION_IDLE_TIMEOUT_MS = 1_000L
        const val SCREEN_SETTLE_MS = 3_000L
    }
}
