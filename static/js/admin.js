/**
 * Kisan Setu - Admin Dashboard JavaScript
 */

function openEditCenterModal(id, name, location, district, state, contact, opening, closing, status, lat, lng) {
    const form = document.getElementById('editCenterForm');
    if (form) {
        form.action = `/admin/centers/${id}/edit`;
    }

    const setVal = (fieldId, val) => {
        const el = document.getElementById(fieldId);
        if (el) el.value = val;
    };

    setVal('edit_center_name', name);
    setVal('edit_center_location', location);
    setVal('edit_center_district', district);
    setVal('edit_center_state', state);
    setVal('edit_center_contact', contact);
    setVal('edit_center_opening', opening);
    setVal('edit_center_closing', closing);
    setVal('edit_center_status', status);
    setVal('edit_center_lat', lat);
    setVal('edit_center_lng', lng);

    const modal = new bootstrap.Modal(document.getElementById('editCenterModal'));
    modal.show();
}

async function adminUpdateTokenStatus(tokenId, newStatus) {
    if (!confirm(`Confirm updating Token #${tokenId} status to ${newStatus}?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/admin/tokens/${tokenId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Token status updated to ${newStatus}.`, 'success');
            setTimeout(() => window.location.reload(), 700);
        } else {
            showToast(data.message || "Failed to update token status.", 'danger');
        }
    } catch (e) {
        showToast("Error updating token status.", 'danger');
    }
}
