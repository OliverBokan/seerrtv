package ca.devmesh.seerrtv.ui.components

import android.content.Context
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ca.devmesh.seerrtv.util.SharedPreferencesUtil
import java.time.format.DateTimeFormatter
import java.time.LocalTime
import java.time.temporal.ChronoUnit
import kotlinx.coroutines.delay
import kotlin.time.Duration.Companion.milliseconds

/**
 * A simple clock component that shows the current time
 * Uses 24-hour or 12-hour format based on user preferences
 */
@Composable
fun Clock(context: Context) {
    // Minute precision: the clock shows hours and minutes, and a value that changed every second
    // recomposed the clock (and re-read the 24-hour preference) every second.
    var currentTime by remember { mutableStateOf(LocalTime.now().truncatedTo(ChronoUnit.MINUTES)) }
    val use24HourClock by rememberUpdatedState(SharedPreferencesUtil.use24HourClock(context))
    val formatter =
            remember(use24HourClock) {
                if (use24HourClock) {
                    DateTimeFormatter.ofPattern("HH:mm")
                } else {
                    DateTimeFormatter.ofPattern("h:mm")
                }
            }

    LaunchedEffect(Unit) {
        while (true) {
            val now = LocalTime.now()
            currentTime = now.truncatedTo(ChronoUnit.MINUTES)
            // Sleep until the next minute starts
            val untilNextMinuteMs = 60_000L - (now.second * 1000L + now.nano / 1_000_000L)
            delay(untilNextMinuteMs.coerceAtLeast(250L).milliseconds)
        }
    }

    Text(
            text = currentTime.format(formatter),
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(end = 8.dp)
    )
} 