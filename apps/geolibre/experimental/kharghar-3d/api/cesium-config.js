export default function handler(request, response) {
  response.setHeader('Cache-Control', 'no-store, max-age=0');
  response.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET');
    return response.status(405).json({ enabled: false, error: 'Only GET is allowed.' });
  }

  const accessToken = process.env.CESIUM_ION_ACCESS_TOKEN;
  const assetId = process.env.CESIUM_ION_ASSET_ID || '2275207';

  if (!accessToken) {
    return response.status(503).json({
      enabled: false,
      error: 'CESIUM_ION_ACCESS_TOKEN is not configured for this deployment.'
    });
  }

  return response.status(200).json({ enabled: true, assetId, accessToken });
}
