export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetUrl = url.searchParams.get("url");

    if (!targetUrl) {
      return new Response("Missing url parameter", { status: 400 });
    }

    // Use caller's User-Agent if provided, otherwise default to Chrome
    const callerUA = request.headers.get("User-Agent") || "";
    const useCallerUA = callerUA.includes("android") || callerUA.includes("com.google");

    const headers = {
      "User-Agent": useCallerUA
        ? callerUA
        : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9",
      "Cookie": "CONSENT=YES+cb.20210328-17-p0.en+FX+634",
    };

    let fetchOptions = { method: "GET", headers };

    // If the incoming request is POST, forward as POST with its body
    if (request.method === "POST") {
      const body = await request.text();
      fetchOptions.method = "POST";
      fetchOptions.body = body;
      headers["Content-Type"] = request.headers.get("Content-Type") || "application/json";
    }

    const response = await fetch(targetUrl, fetchOptions);
    const responseBody = await response.text();

    return new Response(responseBody, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "text/plain",
        "Access-Control-Allow-Origin": "*",
      },
    });
  },
};
