
export const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};

export const validatePassword = (password) => {
    return password.length >= 8;
};

export const validateUsername = (username) => {
    const validCharsRegex = /^[a-zA-Z0-9.]+$/;
    if (!validCharsRegex.test(username)) {
        return false;
    }

    if (username.length < 6) {
        return false;
    }

    const hasLetterRegex = /[a-zA-Z]/;
    if (!hasLetterRegex.test(username)) {
        return false;
    }

    const dotCount = (username.match(/\./g) || []).length;
    if (dotCount > 1) {
        return false;
    }
    
    if (username.startsWith('.') || username.endsWith('.')) {
        return false;
    }

    return true;
};