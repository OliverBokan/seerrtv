package ca.devmesh.seerrtv.navigation

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Guards the route -> screen-name mapping.
 *
 * Why this matters: screens register their DPAD handlers with DpadController under this name.
 * When the search destination became "search?query={query}", splitting on "/" alone produced
 * "search?query={query}", no registered config matched, and every DPAD key on the search screen
 * went unhandled (results unreachable, Enter did nothing).
 */
class BaseRouteTest {

    @Test
    fun `query-only route maps to its name`() {
        assertEquals("search", baseRoute("search?query={query}"))
        assertEquals("search", baseRoute("search?query=dune"))
        assertEquals("search", baseRoute("search"))
    }

    @Test
    fun `path routes map to the first segment`() {
        assertEquals("details", baseRoute("details/{mediaId}/{mediaType}?showRequestModal={showRequestModal}"))
        assertEquals(
            "mediaDiscovery",
            baseRoute("mediaDiscovery/{mediaType}/{categoryId}/{discoveryType}/{categoryName}/{timestamp}?image={image}")
        )
        assertEquals("browse", baseRoute("browse/movies"))
        assertEquals("main", baseRoute("main"))
    }

    @Test
    fun `null route maps to empty`() {
        assertEquals("", baseRoute(null))
    }
}
