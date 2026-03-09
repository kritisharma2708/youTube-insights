export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetUrl = url.searchParams.get("url");
    const method = url.searchParams.get("method") || "GET";

    if (!targetUrl) {
      return new Response("Missing url parameter", { status: 400 });
    }

    // Build the forwarded request options
    const fetchOptions = {
      method: method,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
      },
    };

    // Forward request body for POST requests
    if (method === "POST") {
      const body = url.searchParams.get("body");
      if (body) {
        fetchOptions.body = body;
        fetchOptions.headers["Content-Type"] = "application/json";
      }
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
