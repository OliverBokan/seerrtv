package ca.devmesh.seerrtv.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.ConcurrentHashMap

/**
 * The few fields a home-row card shows (title, artwork, overview) for a TMDB title.
 *
 * Seerr's `/media` and `/request` lists carry only TMDB IDs, so the Recently Added and Recent
 * Requests rows fetch `movie/{id}` or `tv/{id}` for every card. On the test server that is 34
 * calls per home load, each one a TMDB fetch on the server, and they took about 6 s however
 * they were parallelised. These fields rarely change, so they are kept between launches.
 */
@Serializable
data class CardMetadata(
    val id: Int,
    val title: String? = null,
    val name: String? = null,
    val originalTitle: String? = null,
    val overview: String = "",
    val posterPath: String? = null,
    val backdropPath: String? = null
)

/**
 * In-memory map of [CardMetadata] backed by a JSON file in the app's cache directory (Android
 * may clear it; that only costs a refetch). Entries expire after [TTL_MS]. The file is read
 * once, on first use, and written by [persist] after a row finishes loading; both off the
 * main thread.
 */
class CardMetadataStore(private val file: File) {

    @Serializable
    private data class Entry(val meta: CardMetadata, val fetchedAt: Long)

    private val entries = ConcurrentHashMap<String, Entry>()
    private val ioLock = Mutex()
    @Volatile private var loaded = false
    @Volatile private var dirty = false

    suspend fun get(key: String): CardMetadata? {
        ensureLoaded()
        val entry = entries[key] ?: return null
        return entry.meta.takeIf { System.currentTimeMillis() - entry.fetchedAt < TTL_MS }
    }

    fun put(key: String, meta: CardMetadata) {
        entries[key] = Entry(meta, System.currentTimeMillis())
        dirty = true
    }

    /** Writes the entries to disk if anything changed since the last write. */
    suspend fun persist() {
        if (!dirty) return
        ioLock.withLock {
            if (!dirty) return
            dirty = false
            val now = System.currentTimeMillis()
            val keep = entries.entries
                .filter { now - it.value.fetchedAt < TTL_MS }
                .sortedByDescending { it.value.fetchedAt }
                .take(MAX_ENTRIES)
                .associate { it.key to it.value }
            withContext(Dispatchers.IO) {
                try {
                    // Write-then-rename so a crash mid-write never leaves a truncated file.
                    val tmp = File(file.parentFile, file.name + ".tmp")
                    tmp.writeText(json.encodeToString(keep))
                    if (!tmp.renameTo(file)) {
                        file.delete()
                        tmp.renameTo(file)
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "Could not save card metadata: ${e.message}")
                }
            }
        }
    }

    /** Drops everything, in memory and on disk (server change, sign-out). */
    suspend fun clear() {
        ioLock.withLock {
            entries.clear()
            dirty = false
            loaded = true
            withContext(Dispatchers.IO) { file.delete() }
        }
    }

    private suspend fun ensureLoaded() {
        if (loaded) return
        ioLock.withLock {
            if (loaded) return
            val stored = withContext(Dispatchers.IO) {
                try {
                    if (file.exists()) json.decodeFromString<Map<String, Entry>>(file.readText()) else emptyMap()
                } catch (e: Exception) {
                    // Corrupt or from an older format: start empty, it will be rewritten.
                    Log.w(TAG, "Ignoring unreadable card metadata cache: ${e.message}")
                    emptyMap()
                }
            }
            stored.forEach { (key, entry) -> entries.putIfAbsent(key, entry) }
            loaded = true
        }
    }

    private companion object {
        const val TAG = "CardMetadataStore"
        const val TTL_MS = 24 * 60 * 60 * 1000L
        const val MAX_ENTRIES = 500
        val json = Json { ignoreUnknownKeys = true }
    }
}
