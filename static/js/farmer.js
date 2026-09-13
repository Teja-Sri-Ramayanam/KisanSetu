/**
 * Kisan Setu - Farmer Dashboard & Slot Booking JavaScript
 */

let selectedSlotId = null;

function openBookingModal(slotId, centerName, slotDate, startTime, endTime, availableCapacity) {
    selectedSlotId = slotId;
    document.getElementById('modal-center-name').textContent = centerName;
    document.getElementById('modal-slot-date').textContent = slotDate;
    document.getElementById('modal-slot-time').textContent = `${startTime} - ${endTime}`;
    document.getElementById('modal-available-cap').textContent = availableCapacity;

    const form = document.getElementById('bookingModalForm');
    if (form) {
        form.action = `/farmer/book-slot/${slotId}`;
    }

    const modal = new bootstrap.Modal(document.getElementById('bookingConfirmModal'));
    modal.show();
}

// Async Slot Booking via fetch API
async function confirmSlotBooking() {
    if (!selectedSlotId) return;

    const cropType = document.getElementById('modal_crop_type')?.value || 'Paddy / Rice';
    const quantity = parseFloat(document.getElementById('modal_quantity')?.value || 50.0);
    const btn = document.getElementById('btnConfirmBooking');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Booking Slot...';
    }

    try {
        const response = await fetch(`/api/slots/${selectedSlotId}/book`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                crop_type: cropType,
                estimated_quantity_quintals: quantity
            })
        });

        const resData = await response.json();

        if (resData.success) {
            showToast("Slot booked successfully! Redirecting to your token...", "success");
            setTimeout(() => {
                window.location.href = '/farmer/token';
            }, 1000);
        } else {
            showToast(resData.message || "Failed to book slot.", "danger");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Confirm Booking';
            }
        }
    } catch (err) {
        // Fallback to standard form submit if fetch fails
        const form = document.getElementById('bookingModalForm');
        if (form) {
            form.submit();
        } else {
            showToast("Network error. Please try again.", "danger");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Confirm Booking';
            }
        }
    }
}

// Live Queue Refresh for Farmer
async function refreshQueueStatus(tokenId) {
    if (!tokenId) return;

    try {
        const res = await fetch(`/api/queue/${tokenId}`);
        const data = await res.json();

        if (data.success && data.data) {
            const q = data.data;
            const peopleAheadEl = document.getElementById('queue-people-ahead');
            const estTimeEl = document.getElementById('queue-est-time');
            const procTokenEl = document.getElementById('queue-proc-token');
            const statusBadgeEl = document.getElementById('queue-status-badge');
            const progressBarEl = document.getElementById('queue-progress-bar');

            if (peopleAheadEl) peopleAheadEl.textContent = q.people_ahead;
            if (estTimeEl) estTimeEl.textContent = `${q.estimated_waiting_minutes} mins`;
            if (procTokenEl) procTokenEl.textContent = q.current_processing_token || 'None';

            if (statusBadgeEl) {
                statusBadgeEl.textContent = q.status;
                statusBadgeEl.className = `badge-status ${q.status.toLowerCase()}`;
            }

            if (progressBarEl) {
                // Calculate progress: if 0 people ahead, 90%; if completed 100%
                let pct = 20;
                if (q.status === 'Completed') pct = 100;
                else if (q.status === 'Processing') pct = 75;
                else if (q.people_ahead === 0) pct = 50;
                else pct = Math.max(10, Math.min(60, 100 - (q.people_ahead * 15)));

                progressBarEl.style.width = `${pct}%`;
                progressBarEl.setAttribute('aria-valuenow', pct);
            }
        }
    } catch (e) {
        console.error("Queue refresh error:", e);
    }
}
