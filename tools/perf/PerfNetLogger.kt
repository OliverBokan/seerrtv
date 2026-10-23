package ca.devmesh.seerrtv.data

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response

/**
 * MEASUREMENT ONLY — never committed into tv/src. tools/perf/build-instrumented.sh copies this
 * into a scratch worktree and wires it into the API and image OkHttp clients.
 * One logcat line per completed request, parsed by tools/perf/parse_perfnet.py.
 */
class PerfNetLogger(private val kind: String) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val req = chain.request()
        val start = System.currentTimeMillis()
        val resp = chain.proceed(req)
        val end = System.currentTimeMillis()
        val len = resp.body?.contentLength() ?: -1
        val query = req.url.encodedQuery?.let { "?$it" } ?: ""
        Log.d("PerfNet", "$kind ${req.method} ${resp.code} start=$start end=$end len=$len ${req.url.encodedPath}$query")
        return resp
    }
}
