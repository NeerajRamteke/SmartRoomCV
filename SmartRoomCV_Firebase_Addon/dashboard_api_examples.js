// Add these helpers to your existing React/Vite dashboard (do not replace your app).
// The Firebase bridge is local-only at http://127.0.0.1:5001.

const FIREBASE_BRIDGE = "http://127.0.0.1:5001";

export async function getFirebaseCurrent() {
  const response = await fetch(`${FIREBASE_BRIDGE}/api/current`);
  if (!response.ok) throw new Error("Could not load current Firebase state");
  return response.json();
}

export async function getFirebaseHistory(limit = 500) {
  const response = await fetch(
    `${FIREBASE_BRIDGE}/api/history?limit=${encodeURIComponent(limit)}`
  );
  if (!response.ok) throw new Error("Could not load Firebase history");
  return response.json();
}

export async function getFirebaseAnalytics() {
  const response = await fetch(`${FIREBASE_BRIDGE}/api/analytics`);
  if (!response.ok) throw new Error("Could not load Firebase analytics");
  return response.json();
}

// Example usage inside a React component:
// useEffect(() => {
//   getFirebaseAnalytics().then(setAnalytics).catch(console.error);
// }, []);
//
// Useful analytics fields:
// analytics.sample_count
// analytics.average_people
// analytics.peak_people
// analytics.average_active_zones
// analytics.zone_occupancy_samples["1"] ... ["4"]
// analytics.hourly_average_people -> [{ hour, average_people, samples }]
//
// Existing dashboard UI components/styles are not replaced by this file.
