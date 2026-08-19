function showRecommendation() {

    alert(
        "Smart Recommendation:\n\n" +
        "Picking is currently the largest bottleneck.\n\n" +
        "Recommended actions:\n" +
        "1. Prioritize urgent orders.\n" +
        "2. Assign additional picking staff.\n" +
        "3. Pick nearby warehouse locations together.\n" +
        "4. Complete high-priority orders first."
    );
}


// Automatically refresh dashboard data

async function loadAnalytics() {

    try {

        const response =
            await fetch("/api/analytics");

        const data =
            await response.json();

        console.log(
            "Warehouse Analytics:",
            data
        );

    } catch (error) {

        console.error(
            "Analytics error:",
            error
        );
    }
}


loadAnalytics();