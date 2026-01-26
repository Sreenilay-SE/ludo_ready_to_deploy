// =============================================================================
// 🔧 DEPLOYMENT CONFIGURATION
// =============================================================================
// 
// INSTRUCTIONS:
// 1. Deploy backend to Render first
// 2. Copy your Render URL (e.g., https://exitguard-backend-xxxx.onrender.com)
// 3. Replace 'REPLACE_WITH_YOUR_RENDER_URL' below with your actual URL
// 4. Save this file and push to GitHub
// 5. Deploy frontend to Vercel
//
// =============================================================================

const CONFIG = {
    // Backend API URL - UPDATE THIS AFTER DEPLOYING TO RENDER
    BACKEND_URL: 'http://localhost:5000',  // Change to: https://your-app.onrender.com

    // API Key (matches backend .env)
    API_KEY: 'exitguard_demo_key_2026',

    // Session tracking settings
    TRACKING_INTERVAL: 3000,  // Send data every 3 seconds
    SESSION_TIMEOUT: 300000,  // 5 minutes
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
