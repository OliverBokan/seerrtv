package ca.devmesh.seerrtv.navigation

/**
 * The logical screen name for a navigation route pattern or concrete route: its first path
 * segment, without any query string. "search?query={query}" and "search" both map to "search";
 * "details/{mediaId}/{mediaType}?showRequestModal={showRequestModal}" maps to "details".
 *
 * Screens register with DpadController and are matched by TopBar/MainActivity on this name, so
 * splitting on "/" alone breaks as soon as a route gains optional arguments without a path segment.
 */
fun baseRoute(route: String?): String =
    route.orEmpty().substringBefore('?').substringBefore('/')
