package ca.devmesh.seerrtv.ui.components

/**
 * One key per item for a lazy list or grid, built from [baseKey] (an id that stays with the
 * item), with a `#n` suffix on repeats. Lazy layouts crash on duplicate keys, and the same title
 * or person can legitimately appear twice (a person credited for two roles, a movie and a series
 * sharing a TMDB id). Call it inside `remember(items)` so the keys are built once per list.
 */
fun <T> uniqueLazyKeys(items: List<T>, baseKey: (T) -> String): List<String> {
    val seen = HashMap<String, Int>()
    return items.map { item ->
        val base = baseKey(item)
        val n = seen.getOrDefault(base, 0)
        seen[base] = n + 1
        if (n == 0) base else "$base#$n"
    }
}
