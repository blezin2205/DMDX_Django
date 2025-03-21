
function handleDateInput(e) {
    const input = e.target;
    // Store cursor position
    const cursorPos = input.selectionStart;
    const prevLength = input.value.length;
    
    // Remove any non-digit characters
    let value = input.value.replace(/\D/g, '');
    
    // Don't format if less than 1 character
    if (value.length < 1) {
        input.value = value;
        return;
    }

    // Format as YYYY-MM-DD
    let formattedValue = '';
    if (value.length <= 4) {
        formattedValue = value;
    } else if (value.length <= 6) {
        formattedValue = value.substring(0, 4) + '-' + value.substring(4);
    } else {
        formattedValue = value.substring(0, 4) + '-' + value.substring(4, 6) + '-' + value.substring(6, 8);
    }
    
    // Validate month and day if we have a complete date
    if (value.length >= 8) {
        const year = parseInt(value.substring(0, 4));
        const month = parseInt(value.substring(4, 6));
        const day = parseInt(value.substring(6, 8));
        
        let validMonth = month;
        if (month > 12) validMonth = 12;
        if (month < 1) validMonth = 1;
        
        const daysInMonth = new Date(year, validMonth, 0).getDate();
        let validDay = day;
        if (day > daysInMonth) validDay = daysInMonth;
        if (day < 1) validDay = 1;
        
        formattedValue = `${year}-${String(validMonth).padStart(2, '0')}-${String(validDay).padStart(2, '0')}`;
    }
    
    input.value = formattedValue;
    
    // Adjust cursor position if we're not at the end
    if (cursorPos < prevLength) {
        // If we're at a position where a hyphen was removed, move cursor back one space
        const newCursorPos = cursorPos - (prevLength - formattedValue.length);
        input.setSelectionRange(newCursorPos, newCursorPos);
    }
}

function handleDateBlur(e) {
    const value = e.target.value;
    if (value) {
        const date = new Date(value);
        if (isNaN(date.getTime())) {
            e.target.setCustomValidity('Будь ласка, введіть коректну дату у форматі РРРР-ММ-ДД');
        } else {
            e.target.setCustomValidity('');
        }
    }
}
