// ExitGuard Behavior Tracking SDK
// Captures user micro-interactions and sends to backend for churn risk scoring

(function () {
    const BACKEND_URL = 'https://exitguard-backend.onrender.com';
    const API_KEY = 'exitguard_demo_key_2026';
    const SEND_INTERVAL = 10000; // Send events every 10 seconds

    // Generate unique session ID
    const sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

    // Event buffer
    let events = [];
    let behaviorCounts = {
        rageClicks: 0,
        deadClicks: 0,
        idleTime: 0,
        hesitations: 0,
        scrollCount: 0,
        mouseJiggles: 0,
        // New mood-related metrics
        cartRevisits: 0,
        itemAddRemoves: 0,
        scrollDirectionChanges: 0,
        mouseShakeIntensity: 0,
        priceAreaTime: 0,
        modalToggle: 0,
        tabSwitches: 0,
        mouseExitAttempts: 0,
        addToCartActions: 0,
        checkoutAttempts: 0
    };

    // Tracking state
    let lastMouseMove = Date.now();
    let lastClickTime = 0;
    let lastClickPosition = { x: 0, y: 0 };
    let clickCount = 0;
    let hoverStartTime = null;
    let hoverElement = null;
    let lastScrollPosition = 0;
    let scrollDirection = 0;
    let scrollChangeCount = 0;
    let lastCartLength = 0;
    let cartOpenCount = 0;
    let lastMouseY = 0;
    let mouseShakeCount = 0;
    let currentMood = 'neutral';

    // Display session ID on page
    setTimeout(() => {
        const sessionIdEl = document.getElementById('sessionId');
        if (sessionIdEl) {
            sessionIdEl.textContent = sessionId;
        }
    }, 100);

    // Track mouse movement for idle detection
    document.addEventListener('mousemove', function (e) {
        const now = Date.now();
        const timeSinceLastMove = now - lastMouseMove;

        // Detect mouse jiggle (rapid small movements)
        if (timeSinceLastMove < 100) {
            const distance = Math.sqrt(
                Math.pow(e.clientX - (e.clientX - e.movementX), 2) +
                Math.pow(e.clientY - (e.clientY - e.movementY), 2)
            );
            if (distance < 5) {
                behaviorCounts.mouseJiggles++;
            }
        }

        lastMouseMove = now;
    }, { passive: true });

    // Track clicks for rage clicks and dead clicks
    document.addEventListener('click', function (e) {
        const now = Date.now();
        const clickPosition = { x: e.clientX, y: e.clientY };

        // Detect rage clicks (multiple rapid clicks in same area)
        if (now - lastClickTime < 500) {
            const distance = Math.sqrt(
                Math.pow(clickPosition.x - lastClickPosition.x, 2) +
                Math.pow(clickPosition.y - lastClickPosition.y, 2)
            );

            if (distance < 50) {
                clickCount++;
                if (clickCount >= 2) {  // Reduced from 3 to 2 for faster detection
                    behaviorCounts.rageClicks++;
                    events.push({
                        type: 'rage_click',
                        timestamp: now,
                        x: clickPosition.x,
                        y: clickPosition.y,
                        count: clickCount
                    });
                }
            } else {
                clickCount = 1;
            }
        } else {
            clickCount = 1;
        }

        // Detect dead clicks (clicks on truly non-interactive elements)
        // IMPROVED: Only count clicks on dead areas, not content
        const target = e.target;
        const isInteractive = target.tagName === 'A' ||
            target.tagName === 'BUTTON' ||
            target.tagName === 'INPUT' ||
            target.onclick !== null ||
            target.getAttribute('role') === 'button' ||
            window.getComputedStyle(target).cursor === 'pointer';

        // Only count as dead click if clicking truly dead areas
        const isDeadArea = (
            target.tagName === 'BODY' ||
            target.tagName === 'HTML' ||
            (target.classList.contains('container') && !target.closest('a, button, input, [role="button"]'))
        );

        if (!isInteractive && isDeadArea && !target.closest('a, button, input, [role="button"]')) {
            behaviorCounts.deadClicks++;
            events.push({
                type: 'dead_click',
                timestamp: now,
                x: clickPosition.x,
                y: clickPosition.y,
                element: target.tagName
            });
        }

        lastClickTime = now;
        lastClickPosition = clickPosition;
    }, { passive: true });

    // Track hovering/hesitation over buttons
    document.addEventListener('mouseover', function (e) {
        const target = e.target;
        if (target.tagName === 'BUTTON' || target.classList.contains('add-to-cart-btn') ||
            target.classList.contains('checkout-btn')) {
            hoverStartTime = Date.now();
            hoverElement = target;
        }
    }, { passive: true });

    document.addEventListener('mouseout', function (e) {
        if (hoverStartTime && hoverElement === e.target) {
            const hoverDuration = (Date.now() - hoverStartTime) / 1000;
            if (hoverDuration > 5) { // Increased from 2 - users need time to read!
                behaviorCounts.hesitations++;
                events.push({
                    type: 'hesitation',
                    timestamp: Date.now(),
                    duration: hoverDuration,
                    element: e.target.textContent || e.target.tagName
                });
            }
            hoverStartTime = null;
            hoverElement = null;
        }
    }, { passive: true });

    // Track scroll behavior
    document.addEventListener('scroll', function () {
        const currentScroll = window.scrollY;
        const newDirection = currentScroll > lastScrollPosition ? 1 : -1;

        if (scrollDirection !== 0 && newDirection !== scrollDirection) {
            scrollChangeCount++;
        }

        scrollDirection = newDirection;
        lastScrollPosition = currentScroll;
        behaviorCounts.scrollCount++;

        // Detect excessive scrolling (potential confusion)
        if (scrollChangeCount > 5) {
            events.push({
                type: 'excessive_scroll',
                timestamp: Date.now(),
                changes: scrollChangeCount
            });
            scrollChangeCount = 0;
        }
    }, { passive: true });

    // Track idle time
    setInterval(function () {
        const now = Date.now();
        const idleSeconds = (now - lastMouseMove) / 1000;

        if (idleSeconds > 5) { // Idle for more than 5 seconds
            behaviorCounts.idleTime = Math.floor(idleSeconds);
            events.push({
                type: 'idle',
                timestamp: now,
                duration: idleSeconds
            });
        }
    }, 5000);

    // === MOOD DETECTION: Track exit intent (mouse moving toward browser controls) ===
    document.addEventListener('mousemove', function (e) {
        // Track upward movement toward browser controls
        if (e.clientY < 50 && lastMouseY >= 50) {
            behaviorCounts.mouseExitAttempts++;
            events.push({
                type: 'exit_intent',
                timestamp: Date.now(),
                y_position: e.clientY
            });
        }

        // Detect mouse shake (rapid vertical movements - frustration indicator)
        if (Math.abs(e.clientY - lastMouseY) > 30 && Math.abs(e.movementY) > 15) {
            mouseShakeCount++;
            if (mouseShakeCount > 3) {
                behaviorCounts.mouseShakeIntensity++;
                mouseShakeCount = 0;
            }
        }

        lastMouseY = e.clientY;
    }, { passive: true });

    // === MOOD DETECTION: Track cart hesitation ===
    window.addEventListener('cartOpened', function (e) {
        cartOpenCount++;
        if (cartOpenCount > 2) {
            behaviorCounts.cartRevisits = cartOpenCount;
        }
    });

    // === MOOD DETECTION: Track add to cart actions ===
    window.addEventListener('itemAdded', function (e) {
        behaviorCounts.addToCartActions++;
    });

    // === MOOD DETECTION: Track item additions/removals ===
    window.addEventListener('cartChanged', function (e) {
        const cartLength = e.detail.cartLength || 0;
        if (lastCartLength > 0 && cartLength < lastCartLength) {
            behaviorCounts.itemAddRemoves++;
        }
        lastCartLength = cartLength;
    });

    // === MOOD DETECTION: Track price area hovering ===
    document.addEventListener('mouseover', function (e) {
        const target = e.target;
        if (target.classList.contains('product-price') ||
            target.classList.contains('cart-total') ||
            target.closest('.product-price, .cart-total')) {
            hoverStartTime = Date.now();
            hoverElement = target;
        }
    }, { passive: true });

    document.addEventListener('mouseout', function (e) {
        if (hoverStartTime && (
            e.target.classList.contains('product-price') ||
            e.target.classList.contains('cart-total') ||
            e.target.closest('.product-price, .cart-total')
        )) {
            const hoverDuration = (Date.now() - hoverStartTime) / 1000;
            if (hoverDuration > 3) {
                behaviorCounts.priceAreaTime += hoverDuration;
            }
            hoverStartTime = null;
            hoverElement = null;
        }
    }, { passive: true });

    // === MOOD DETECTION: Track modal toggles ===
    window.addEventListener('modalToggled', function (e) {
        behaviorCounts.modalToggle = (behaviorCounts.modalToggle || 0) + 1;
    });

    // === MOOD DETECTION: Track tab visibility changes (distraction/leaving) ===
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            behaviorCounts.tabSwitches++;
        }
    });

    // === MOOD DETECTION: Track scroll direction changes (confusion indicator) ===
    document.addEventListener('scroll', function () {
        const currentScroll = window.scrollY;
        const newDirection = currentScroll > lastScrollPosition ? 1 : -1;

        if (scrollDirection !== 0 && newDirection !== scrollDirection) {
            behaviorCounts.scrollDirectionChanges++;
        }

        scrollDirection = newDirection;
        lastScrollPosition = currentScroll;
    }, { passive: true });

    // === Mood Scoring Algorithm ===
    function determineMood() {
        const moodScores = {
            frustrated: 0,
            hesitating: 0,
            confused: 0,
            priceSensitive: 0,
            aboutToLeave: 0,
            engaged: 0
        };

        // FRUSTRATED indicators
        if (behaviorCounts.rageClicks > 1) moodScores.frustrated += 40;
        if (behaviorCounts.deadClicks > 2) moodScores.frustrated += 25;
        if (behaviorCounts.mouseShakeIntensity > 2) moodScores.frustrated += 30;
        if (behaviorCounts.modalToggle > 4) moodScores.frustrated += 20;

        // HESITATING indicators
        if (behaviorCounts.cartRevisits > 2) moodScores.hesitating += 50;
        if (behaviorCounts.hesitations > 3) moodScores.hesitating += 30;
        if (behaviorCounts.checkoutAttempts === 0 && behaviorCounts.addToCartActions > 2) {
            moodScores.hesitating += 40;
        }
        if (behaviorCounts.itemAddRemoves > 1) moodScores.hesitating += 35;

        // CONFUSED indicators
        if (behaviorCounts.scrollDirectionChanges > 6) moodScores.confused += 40;
        if (behaviorCounts.deadClicks > 1 && behaviorCounts.rageClicks === 0) {
            moodScores.confused += 30;
        }
        if (behaviorCounts.modalToggle > 2 && behaviorCounts.modalToggle < 5) {
            moodScores.confused += 25;
        }

        // PRICE-SENSITIVE indicators
        if (behaviorCounts.priceAreaTime > 10) moodScores.priceSensitive += 50;
        if (behaviorCounts.cartRevisits > 1) moodScores.priceSensitive += 30;
        if (behaviorCounts.itemAddRemoves > 0) moodScores.priceSensitive += 40;

        // ABOUT TO LEAVE indicators
        if (behaviorCounts.mouseExitAttempts > 1) moodScores.aboutToLeave += 60;
        if (behaviorCounts.idleTime > 15) moodScores.aboutToLeave += 40;
        if (behaviorCounts.tabSwitches > 2) moodScores.aboutToLeave += 35;

        // ENGAGED indicators (positive signals)
        if (behaviorCounts.addToCartActions > 2 && behaviorCounts.rageClicks === 0) {
            moodScores.engaged += 50;
        }
        if (behaviorCounts.scrollCount > 5 && behaviorCounts.scrollDirectionChanges < 3) {
            moodScores.engaged += 30;
        }
        if (behaviorCounts.deadClicks === 0 && behaviorCounts.rageClicks === 0) {
            moodScores.engaged += 20;
        }

        // Find highest mood score
        let highestMood = 'neutral';
        let highestScore = 0;

        for (const [mood, score] of Object.entries(moodScores)) {
            if (score > highestScore && score > 20) { // Threshold of 20
                highestScore = score;
                highestMood = mood;
            }
        }

        return {
            mood: highestMood,
            scores: moodScores,
            confidence: highestScore
        };
    }

    // Send events to backend

    async function sendEvents() {
        if (events.length === 0 && Object.values(behaviorCounts).every(v => v === 0)) {
            return;
        }

        // Calculate current mood
        const moodData = determineMood();
        const previousMood = currentMood;
        currentMood = moodData.mood;

        try {
            const response = await fetch(BACKEND_URL + '/api/track', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    timestamp: Date.now(),
                    events: events,
                    behaviors: { ...behaviorCounts },
                    mood: moodData.mood,
                    moodScores: moodData.scores,
                    moodConfidence: moodData.confidence
                })
            });

            if (response.ok) {
                const data = await response.json();

                // Update risk score on page
                const riskScoreEvent = new CustomEvent('riskScoreUpdate', {
                    detail: {
                        riskScore: data.risk_score,
                        rootCause: data.root_cause,
                        suggestedAction: data.suggested_action
                    }
                });
                window.dispatchEvent(riskScoreEvent);

                // Dispatch mood change event if mood changed
                if (currentMood !== previousMood && currentMood !== 'neutral') {
                    const moodEvent = new CustomEvent('moodChange', {
                        detail: {
                            mood: currentMood,
                            previousMood: previousMood,
                            confidence: moodData.confidence,
                            scores: moodData.scores
                        }
                    });
                    window.dispatchEvent(moodEvent);

                    console.log(`🎭 Mood changed: ${previousMood} → ${currentMood} (confidence: ${moodData.confidence})`);
                }

                // Clear events buffer
                events = [];
            } else {
                console.warn('Failed to send tracking data:', response.status);
            }
        } catch (error) {
            console.warn('ExitGuard tracking error:', error.message);
            // Silently fail - don't disrupt user experience
        }
    }

    // Mark when intervention is triggered
    async function markIntervention() {
        try {
            await fetch(BACKEND_URL + '/api/intervention', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    intervention_type: 'discount_popup',
                    timestamp: Date.now()
                })
            });
            console.log('Intervention marked for session:', sessionId);
        } catch (error) {
            console.warn('Failed to mark intervention:', error.message);
        }
    }

    // Expose markIntervention globally for demo-store.html
    window.ExitGuard = {
        sessionId: sessionId,
        markIntervention: markIntervention
    };

    // Send events periodically
    setInterval(sendEvents, SEND_INTERVAL);

    // Send events before page unload
    window.addEventListener('beforeunload', function () {
        if (events.length > 0 || Object.values(behaviorCounts).some(v => v > 0)) {
            navigator.sendBeacon(BACKEND_URL + '/api/track', JSON.stringify({
                session_id: sessionId,
                timestamp: Date.now(),
                events: events,
                behaviors: behaviorCounts
            }));
        }
    });

    console.log('ExitGuard Tracker initialized - Session ID:', sessionId);
})();
