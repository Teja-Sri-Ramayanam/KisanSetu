/**
 * Kisan Setu - Procurement Officer JavaScript
 */

// Update token status via API or form
async function updateTokenStatus(tokenId, newStatus, btnElement) {
    if (!confirm(`Are you sure you want to change status to "${newStatus}"?`)) {
        return;
    }

    const originalText = btnElement ? btnElement.innerHTML : '';
    if (btnElement) {
        btnElement.disabled = true;
        btnElement.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }

    try {
        let endpoint = `/api/officer/tokens/${tokenId}/status`;
        let method = 'PUT';
        let body = JSON.stringify({ status: newStatus });

        if (newStatus === 'Completed') {
            endpoint = `/api/officer/tokens/${tokenId}/complete`;
            method = 'POST';
            body = null;
        }

        const res = await fetch(endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: body
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Status updated to ${newStatus} successfully!`, "success");
            setTimeout(() => {
                window.location.reload();
            }, 800);
        } else {
            showToast(data.message || "Failed to update status.", "danger");
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = originalText;
            }
        }
    } catch (err) {
        showToast("Error updating status. Please try standard form.", "danger");
        if (btnElement) {
            btnElement.disabled = false;
            btnElement.innerHTML = originalText;
        }
    }
}
