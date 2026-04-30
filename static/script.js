let updateTimeout = null;
let currentData = {
    client_id: '',
    booked_date: '',
    passenger_first_name: '',
    passenger_last_name: '',
    trip_reason: '',
    travel_type: '',
    type_of_traveller: '',
    project_code: '',
    airline_code: '',
    flight_number: ''
};

function cleanInputValue(value) {
    if (typeof value === 'string') {
        return value;
    }
    return value;
}

function cleanAllData() {
    return;
}

function validatePassengerName(name) {
    if (!name || name.trim() === '') {
        return { valid: false, message: '⚠️ الرجاء إدخال اسم الراكب' };
    }
    
    if (!name.includes('/')) {
        return { 
            valid: false, 
            message: '⚠️ صيغة الاسم غير صحيحة! يرجى استخدام الصيغة: الكنية/الاسم الأول\nمثال: MANSOURI/AHMED' 
        };
    }
    
    const parts = name.split('/');
    if (parts.length < 2) {
        return { 
            valid: false, 
            message: '⚠️ صيغة الاسم غير صحيحة! يرجى الفصل بين الكنية والاسم الأول باستخدام /\nمثال: MANSOURI/AHMED' 
        };
    }
    
    if (parts[0].trim() === '' || parts[1].trim() === '') {
        return { 
            valid: false, 
            message: '⚠️ كل من الكنية والاسم الأول مطلوبان! يرجى إدخال: الكنية/الاسم الأول' 
        };
    }
    
    return { valid: true, message: '✓ صيغة الاسم صحيحة' };
}

function showFieldError(inputElement, message, isError = true) {
    const existingError = inputElement.parentElement.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    const errorSpan = document.createElement('div');
    errorSpan.className = `field-error ${isError ? 'error' : 'success'}`;
    errorSpan.style.cssText = isError ? 
        'color: #dc3545; font-size: 11px; margin-top: 4px;' : 
        'color: #28a745; font-size: 11px; margin-top: 4px;';
    errorSpan.innerText = message;
    inputElement.parentElement.appendChild(errorSpan);
    
    inputElement.style.borderColor = isError ? '#dc3545' : '#28a745';
    
    if (isError) {
        setTimeout(() => {
            if (inputElement.parentElement.querySelector('.field-error') === errorSpan) {
                errorSpan.remove();
                inputElement.style.borderColor = '';
            }
        }, 5000);
    } else {
        setTimeout(() => {
            if (inputElement.parentElement.querySelector('.field-error') === errorSpan) {
                errorSpan.remove();
                inputElement.style.borderColor = '';
            }
        }, 2000);
    }
}

function showAlertMessage(message, isError = true) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `custom-alert ${isError ? 'alert-error' : 'alert-success'}`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        left: auto;
        padding: 15px 20px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ${isError ? 'background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;' : 'background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;'}
    `;
    alertDiv.innerHTML = message.replace(/\n/g, '<br>');
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (alertDiv.parentNode) alertDiv.parentNode.removeChild(alertDiv);
        }, 300);
    }, 5000);
}

function validateBeforeExport() {
    const passengerNameInput = document.querySelector('[data-field="passenger_name"]');
    const passengerName = passengerNameInput?.value || '';
    
    const validation = validatePassengerName(passengerName);
    
    if (!validation.valid) {
        showFieldError(passengerNameInput, validation.message, true);
        passengerNameInput.focus();
        showAlertMessage(validation.message, true);
        return false;
    }
    
    const invoiceNumber = document.querySelector('[data-field="invoice_number"]')?.value || '';
    if (!invoiceNumber.trim()) {
        const invoiceInput = document.querySelector('[data-field="invoice_number"]');
        showFieldError(invoiceInput, '⚠️ الرجاء إدخال رقم الفاتورة', true);
        invoiceInput.focus();
        showAlertMessage('⚠️ الرجاء إدخال رقم الفاتورة', true);
        return false;
    }
    
    return true;
}

function setupInputCleaning() {
    document.querySelectorAll('.form-input:not(select)').forEach(input => {
        input.addEventListener('blur', () => {
            const field = input.dataset.field;
            if (field && currentData[field] !== undefined) {
                currentData[field] = input.value;
                updateTicketDisplay();
            }
        });
    });
    
    document.querySelectorAll('.form-select').forEach(select => {
        select.addEventListener('change', () => {
            const field = select.dataset.field;
            if (field) {
                currentData[field] = select.value;
                updateTicketDisplay();
            }
        });
    });
}

document.querySelectorAll('.form-input').forEach(input => {
    input.addEventListener('input', () => {
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(() => {
            updateTicketDisplay();
        });
    });
    
    input.addEventListener('blur', () => {
        const field = input.dataset.field;
        if (field) {
            currentData[field] = input.value;
            updateTicketDisplay();
        }
    });
});

document.querySelectorAll('.form-select').forEach(select => {
    select.addEventListener('change', () => {
        const field = select.dataset.field;
        if (field) {
            currentData[field] = select.value;
            updateTicketDisplay();
        }
    });
});

function updateTicketDisplay() {
    document.querySelectorAll('.form-input:not(select)').forEach(input => {
        const field = input.dataset.field;
        let value = input.value;
        if (field) currentData[field] = value;
    });
    
    document.querySelectorAll('.form-select').forEach(select => {
        const field = select.dataset.field;
        if (field) {
            currentData[field] = select.value;
        }
    });
    
    const passengerName = currentData.passenger_name || '';
    const passengerNameInput = document.querySelector('[data-field="passenger_name"]');
    if (passengerName && passengerNameInput && passengerName.includes('/')) {
        const validation = validatePassengerName(passengerName);
        if (!validation.valid) {
            showFieldError(passengerNameInput, validation.message, true);
        } else {
            showFieldError(passengerNameInput, validation.message, false);
        }
    }
    
    const fare = parseFloat(currentData.fare) || 0;
    const lskFee = parseFloat(currentData.lsk_fee) || 0;
    const baseFare = parseFloat(currentData.base_fare) || 0;
    const total = fare + lskFee ;
    currentData.total = total;
    document.getElementById('totalAmount').innerText = total;
    
    let html = `
        <div class="section-divider">
            <div class="section-title-ticket">📄 INVOICE DETAILS</div>
            <div class="ticket-field"><div class="ticket-label">Invoice Number:</div><div class="ticket-value">${escapeHtml(currentData.invoice_number) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Invoice Date:</div><div class="ticket-value">${escapeHtml(currentData.invoice_date) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Date of Issue:</div><div class="ticket-value">${escapeHtml(currentData.date_supply) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Project Manager Email:</div><div class="ticket-value">${escapeHtml(currentData.pm_email) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Approver:</div><div class="ticket-value">${escapeHtml(currentData.approver) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Traveller Booker Email:</div><div class="ticket-value">${escapeHtml(currentData.booker_email) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Booked By:</div><div class="ticket-value">${escapeHtml(currentData.booked_by) || '---'}</div></div>
        </div>
        
        <div class="section-divider">
            <div class="section-title-ticket">👤 PASSENGER & BOOKING</div>
            <div class="ticket-field"><div class="ticket-label">Passenger Name:</div><div class="ticket-value">${escapeHtml(currentData.passenger_name) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Employee ID:</div><div class="ticket-value">${escapeHtml(currentData.employee_id) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Business Unit:</div><div class="ticket-value">${escapeHtml(currentData.business_unit) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Cost Center:</div><div class="ticket-value">${escapeHtml(currentData.cost_center) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Trip Reason:</div><div class="ticket-value">${escapeHtml(currentData.trip_reason) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label">Booking Number:</div><div class="ticket-value">${escapeHtml(currentData.booking_number) || '---'}</div></div>
        </div>
        
        <div class="section-divider">
            <div class="section-title-ticket">💰 FINANCIALS</div>
            <div class="ticket-field"><div class="ticket-label">Fare (Ex VAT):</div><div class="ticket-value">${currentData.fare || '0'} USD</div></div>
            <div class="ticket-field"><div class="ticket-label">LSK Fee / Commission:</div><div class="ticket-value">${currentData.lsk_fee || '0'} USD</div></div>
            <div class="ticket-field"><div class="ticket-label">Base Fare:</div><div class="ticket-value">${currentData.base_fare || '0'} USD</div></div>
            <div class="ticket-field"><div class="ticket-label">Ticket Number:</div><div class="ticket-value">${escapeHtml(currentData.ticket_number) || '---'}</div></div>
            <div class="ticket-field"><div class="ticket-label" style="font-weight:700;">TOTAL:</div><div class="ticket-value" style="font-weight:700;color:#667eea;">${total} USD</div></div>
        </div>
    `;
    
    if (currentData.segments && currentData.segments.length > 0) {
        html += `<div class="section-divider"><div class="section-title-ticket">✈️ FLIGHT SEGMENTS</div>`;
        currentData.segments.forEach(seg => {
            html += `
                <div class="ticket-field">
                    <div class="ticket-label">${escapeHtml(seg.flight_number) || 'Flight'}</div>
                    <div class="ticket-value">${escapeHtml(seg.route_name) || ''} | ${escapeHtml(seg.origin) || ''} → ${escapeHtml(seg.destination) || ''} | ${escapeHtml(seg.depart_date) || ''} ${escapeHtml(seg.depart_time) || ''}</div>
                </div>
            `;
        });
        html += `</div>`;
    }
    
    if (currentData.hotel && currentData.hotel.hotel_name) {
        html += `
            <div class="section-divider">
                <div class="section-title-ticket">🏨 HOTEL DETAILS</div>
                <div class="ticket-field"><div class="ticket-label">Hotel Name:</div><div class="ticket-value">${escapeHtml(currentData.hotel.hotel_name) || '---'}</div></div>
                <div class="ticket-field"><div class="ticket-label">Location:</div><div class="ticket-value">${escapeHtml(currentData.hotel.location) || '---'}</div></div>
                <div class="ticket-field"><div class="ticket-label">Number of Nights:</div><div class="ticket-value">${escapeHtml(currentData.hotel.nights) || '---'}</div></div>
                <div class="ticket-field"><div class="ticket-label">Check In:</div><div class="ticket-value">${escapeHtml(currentData.hotel.check_in) || '---'}</div></div>
                <div class="ticket-field"><div class="ticket-label">Check Out:</div><div class="ticket-value">${escapeHtml(currentData.hotel.check_out) || '---'}</div></div>
            </div>
        `;
    }
    
    document.getElementById('ticketContent').innerHTML = html;
    if (currentData.ticket_number) {
        document.getElementById('ticketTicketNumber').innerHTML = `TKT: ${escapeHtml(currentData.ticket_number)}`;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById('addSegmentBtn').addEventListener('click', () => {
    const container = document.getElementById('segmentsContainer');
    const segmentId = Date.now();
    const segmentHtml = `
        <div class="segment-item" data-segment-id="${segmentId}">
            <button class="btn-remove" onclick="removeSegment(${segmentId})">✖</button>
            <div class="form-group"><input type="text" class="form-input" placeholder="Airline Code (e.g. 8Y)" data-seg-field="airline_code"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Route Name" data-seg-field="route_name"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Origin (e.g. NQY)" data-seg-field="origin"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Destination (e.g. LGW)" data-seg-field="destination"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Depart Date (DD/MM/YYYY)" data-seg-field="depart_date"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Depart Time (HH:MM)" data-seg-field="depart_time"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Arrival Date (DD/MM/YYYY)" data-seg-field="arrival_date"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Arrival Time (HH:MM)" data-seg-field="arrival_time"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Class (Y/B/E)" data-seg-field="class_name" value="Y"></div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', segmentHtml);
    
    document.querySelectorAll(`[data-segment-id="${segmentId}"] .form-input`).forEach(input => {
        input.addEventListener('blur', () => {
        });
        input.addEventListener('input', () => {
            clearTimeout(updateTimeout);
            updateTimeout = setTimeout(() => {
                updateSegmentsData();
                updateTicketDisplay();
            });
        });
    });
});

document.getElementById('addHotelBtn').addEventListener('click', () => {
    const container = document.getElementById('hotelContainer');
    const hotelHtml = `
        <div class="hotel-item">
            <div class="form-group"><input type="text" class="form-input" placeholder="Hotel Name" data-hotel-field="hotel_name"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Location" data-hotel-field="location"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Number of Nights" data-hotel-field="nights"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Check In (DD/MM/YYYY)" data-hotel-field="check_in"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Check Out (DD/MM/YYYY)" data-hotel-field="check_out"></div>
            <div class="form-group"><input type="text" class="form-input" placeholder="Destination Code" data-hotel-field="dest_code"></div>
            <button class="btn-remove" onclick="removeHotel()">✖ Remove Hotel</button>
        </div>
    `;
    container.innerHTML = hotelHtml;
    
    document.querySelectorAll('[data-hotel-field]').forEach(input => {
        input.addEventListener('blur', () => {
        });
        input.addEventListener('input', () => {
            clearTimeout(updateTimeout);
            updateTimeout = setTimeout(() => {
                updateHotelData();
                updateTicketDisplay();
            });
        });
    });
});

function updateSegmentsData() {
    const segments = [];
    document.querySelectorAll('.segment-item').forEach(segment => {
        const segData = {};
        segment.querySelectorAll('[data-seg-field]').forEach(input => {
            const field = input.dataset.segField;
            let value = input.value;
            segData[field] = value;
        });
        if (Object.keys(segData).length > 0 && (segData.flight_number || segData.airline_code)) {
            segments.push(segData);
        }
    });
    currentData.segments = segments;
}

function updateHotelData() {
    const hotel = {};
    document.querySelectorAll('[data-hotel-field]').forEach(input => {
        const field = input.dataset.hotelField;
        let value = input.value;
        hotel[field] = value;
    });
    currentData.hotel = hotel;
}

function removeSegment(segmentId) {
    document.querySelector(`[data-segment-id="${segmentId}"]`).remove();
    updateSegmentsData();
    updateTicketDisplay();
}

function removeHotel() {
    document.getElementById('hotelContainer').innerHTML = '';
    delete currentData.hotel;
    updateTicketDisplay();
}

async function handleResponse(response, successMessage, errorMessagePrefix) {
    if (response.ok) {
        return true;
    } else {
        try {
            const errorData = await response.json();
            const errorMsg = errorData.error || errorData.message || 'Unknown error';
            showAlertMessage(errorMsg, true);
        } catch (e) {
            showAlertMessage(`${errorMessagePrefix}: Server error`, true);
        }
        return false;
    }
}

const getHourMinute = () => String(new Date().getHours()).padStart(2, '0') + String(new Date().getMinutes()).padStart(2, '0');

document.getElementById('exportPdfBtn').addEventListener('click', async () => {
    if (!validateBeforeExport()) {
        return;
    }
    
    updateSegmentsData();
    updateHotelData();
    
    try {
        const response = await fetch('/generate_pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentData)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            let invoiceNumber = currentData.invoice_number || 'ticket';
            invoiceNumber = invoiceNumber.replace(/[\\/*?:"<>|]/g, '');
            const fileName = `INV_${invoiceNumber}_${getHourMinute()}.pdf`;
            a.download = fileName;
            
            a.click();
            URL.revokeObjectURL(url);
            showAlertMessage('✓ تم إنشاء ملف PDF بنجاح', false);
        } else {
            const errorData = await response.json();
            showAlertMessage(errorData.error || 'حدث خطأ أثناء إنشاء PDF', true);
        }
    } catch (error) {
        showAlertMessage('حدث خطأ في الاتصال بالخادم', true);
    }
});

document.getElementById('exportXmlBtn').addEventListener('click', async () => {
    if (!validateBeforeExport()) {
        return;
    }
    
    updateSegmentsData();
    updateHotelData();
    
    try {
        const response = await fetch('/generate_excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentData)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            let invoiceNumber = currentData.invoice_number || 'INVOICE';
            invoiceNumber = invoiceNumber.replace(/[\\/*?:"<>|]/g, '');
            a.download = `INV_${invoiceNumber}_TICKET_FILES.zip`;
            
            a.click();
            URL.revokeObjectURL(url);
            showAlertMessage('✓ تم إنشاء ملفات Excel بنجاح', false);
        } else {
            const errorData = await response.json();
            showAlertMessage(errorData.error || 'حدث خطأ أثناء إنشاء ملفات Excel', true);
        }
    } catch (error) {
        showAlertMessage('حدث خطأ في الاتصال بالخادم', true);
    }
});

document.getElementById('sendEmailBtn').addEventListener('click', async () => {
    if (!validateBeforeExport()) {
        return;
    }
    
    const recipientEmail = prompt('Enter client email address:', currentData.booker_email || '');
    if (!recipientEmail) return;
    
    currentData.recipient_email = recipientEmail;
    
    try {
        const response = await fetch('/send_email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentData)
        });
        
        const result = await response.json();
        if (result.success) {
            showAlertMessage('✓ تم إرسال البريد الإلكتروني بنجاح مع المرفقات', false);
        } else {
            showAlertMessage(result.message || 'حدث خطأ أثناء إرسال البريد الإلكتروني', true);
        }
    } catch (error) {
        showAlertMessage('حدث خطأ في الاتصال بالخادم', true);
    }
});
function validatePassengerName(name) {
    if (!name || name.trim() === '') {
        return { valid: false, message: '⚠️ الرجاء إدخال اسم الراكب' };
    }
    
    if (!name.includes('/')) {
        return { 
            valid: false, 
            message: '⚠️ صيغة الاسم غير صحيحة!\n\nالرجاء استخدام الصيغة التالية:\nالكنية/الاسم الأول\n\nمثال: MANSOURI/AHMED أو Hamza/Mohammed\n\n📝 ملاحظة: قم بكتابة الكنية ثم شرطة مائلة / ثم الاسم الأول'
        };
    }
    
    const parts = name.split('/');
    if (parts.length < 2) {
        return { 
            valid: false, 
            message: '⚠️ صيغة الاسم غير صحيحة!\n\nالرجاء الفصل بين الكنية والاسم الأول باستخدام /\n\nمثال: MANSOURI/AHMED أو Hamza/Mohammed' 
        };
    }
    
    if (parts[0].trim() === '' || parts[1].trim() === '') {
        return { 
            valid: false, 
            message: '⚠️ كل من الكنية والاسم الأول مطلوبان!\n\nيرجى إدخال: الكنية/الاسم الأول\n\nمثال: MANSOURI/AHMED أو Hamza/Mohammed' 
        };
    }
    
    return { valid: true, message: '✓ صيغة الاسم صحيحة' };
}

function validateBeforeExport() {
    const passengerNameInput = document.querySelector('[data-field="passenger_name"]');
    const passengerName = passengerNameInput?.value || '';
    
    const validation = validatePassengerName(passengerName);
    
    if (!validation.valid) {
        showFieldError(passengerNameInput, validation.message, true);
        
        passengerNameInput.style.borderColor = '#dc3545';
        passengerNameInput.style.backgroundColor = '#fff8f8';
        
        passengerNameInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        showAlertMessage(validation.message, true);
        
        let hintElement = document.getElementById('name-format-hint');
        if (!hintElement) {
            hintElement = document.createElement('div');
            hintElement.id = 'name-format-hint';
            passengerNameInput.parentElement.appendChild(hintElement);
        }
        
        passengerNameInput.focus();
        return false;
    }
    
    const hintElement = document.getElementById('name-format-hint');
    if (hintElement) {
        hintElement.remove();
    }
    passengerNameInput.style.borderColor = '';
    passengerNameInput.style.backgroundColor = '';
    
    const invoiceNumber = document.querySelector('[data-field="invoice_number"]')?.value || '';
    if (!invoiceNumber.trim()) {
        const invoiceInput = document.querySelector('[data-field="invoice_number"]');
        showFieldError(invoiceInput, '⚠️ الرجاء إدخال رقم الفاتورة', true);
        invoiceInput.focus();
        showAlertMessage('⚠️ الرجاء إدخال رقم الفاتورة', true);
        return false;
    }
    
    return true;
}

function setupPassengerNameValidation() {
    const passengerInput = document.querySelector('[data-field="passenger_name"]');
    if (!passengerInput) return;
    
    passengerInput.addEventListener('blur', () => {
        const name = passengerInput.value;
        if (name && name.trim() !== '') {
            if (!name.includes('/')) {
                showFieldError(passengerInput, '⚠️ يجب أن يحتوي الاسم على شرطة مائلة / مثال: Hamza/Mohammed', true);
                passengerInput.style.borderColor = '#ffc107';
                passengerInput.style.backgroundColor = '#fffbf0';
            } else {
                const existingError = passengerInput.parentElement.querySelector('.field-error');
                if (existingError && existingError.innerText.includes('شرطة مائلة')) {
                    existingError.remove();
                }
                passengerInput.style.borderColor = '#28a745';
                passengerInput.style.backgroundColor = '#f0fff4';
                
                setTimeout(() => {
                    if (passengerInput.style.borderColor === 'rgb(40, 167, 69)') {
                        passengerInput.style.borderColor = '';
                        passengerInput.style.backgroundColor = '';
                    }
                }, 2000);
            }
        }
    });
    
    passengerInput.addEventListener('input', () => {
        passengerInput.style.borderColor = '';
        passengerInput.style.backgroundColor = '';
        const existingError = passengerInput.parentElement.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    });
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', () => {
    setupInputCleaning();
    setupPassengerNameValidation();
});
