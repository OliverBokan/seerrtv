package ca.devmesh.seerrtv.model

import ca.devmesh.seerrtv.data.seerrApiJson
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MediaRequestBodyTest {
    private fun encode(body: MediaRequestBody): JsonObject =
        seerrApiJson.parseToJsonElement(seerrApiJson.encodeToString(MediaRequestBody.serializer(), body)) as JsonObject

    @Test
    fun omitsTagsWhenNoneArePicked() {
        // An explicit empty list would replace the Sonarr/Radarr default tags configured in Seerr.
        assertFalse("tags" in encode(MediaRequestBody(mediaType = "tv", mediaId = 1)))
    }

    @Test
    fun sendsPickedTagsAsNumbers() {
        // Seerr compares request tags with its numeric defaults, as its own web app sends them.
        val tags = encode(MediaRequestBody(mediaType = "movie", mediaId = 1, tags = listOf(3, 7)))["tags"] as JsonArray
        assertTrue(tags.all { !it.jsonPrimitive.isString })
        assertEquals(listOf(3, 7), tags.map { it.jsonPrimitive.int })
    }
}
