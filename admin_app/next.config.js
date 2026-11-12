module.exports = {
  output: "standalone",
  // The BFF (/bff/*) forwards paths to core_backend exactly as the generated API
  // client builds them, and FastAPI collection routes end in "/" (e.g.
  // /content/). Without this, Next.js would redirect /bff/content/ to
  // /bff/content and the backend would no longer match it.
  skipTrailingSlashRedirect: true,
};
