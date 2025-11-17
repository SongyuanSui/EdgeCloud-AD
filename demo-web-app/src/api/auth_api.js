import axios from 'axios';

const SERVER_IP = "api.ts.autoedge.ai";
const ROUTE = "api/auth";
const CONNECTION = "https";

export const login = async (username, password) => {
    try {
        const user = {
            username,
            password
        };
        const response = await axios.post(`${CONNECTION}://${SERVER_IP}/${ROUTE}/login`, user, { withCredentials: true });
        return response;
    } catch (error) {
        console.error('Error login', error);
        throw error;
    }
};

export const logout = async () => {
    try {
        const response = await axios.post(`${CONNECTION}://${SERVER_IP}/${ROUTE}/logout`, {}, { withCredentials: true });
        return response;
    } catch (error) {
        console.error('Error login', error);
        throw error;
    }
};

export const checkLogin = async () => {
    try {
        const response = await axios.get(
            `${CONNECTION}://${SERVER_IP}/${ROUTE}/check`, 
            { 
                withCredentials: true,
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Auth-Check': 'true'
                }
            }
        );
        return response;
    } catch (error) {
        console.error('Error check login:', error);
        throw error;
    }
};


export const register = async (firstName, lastName, organization, username, password, email) => {
    try {
        const user = {
            firstName,
            lastName,
            organization,
            username,
            password,
            email
        };

        const response = await axios.post(`${CONNECTION}://${SERVER_IP}/${ROUTE}/register`, user, { withCredentials: true });
        return {
            success: true,
            status: response.status,
            data: response.data,
            error: null
        };
    } catch (error) {
        //console.error('DEBUG ERROR: Register request failed', error);
        return {
            success: false,
            status: error.response?.status || 500,
            data: null,
            error: {
                details: error.response?.data?.details || error.response?.data?.error || 'Failed to register'
            }
        };
    }
};

export const resendVerificationEmail = async (email) => {
    try {
        const response = await axios.post(
            `${CONNECTION}://${SERVER_IP}/${ROUTE}/resend-verification`,
            { email },
            { withCredentials: true }
        );
        return {
            success: true,
            status: response.status,
            data: response.data,
            error: null
        };
    } catch (error) {
        return {
            success: false,
            status: error.response?.status || 500,
            data: null,
            error: {
                details: error.response?.data?.details || error.response?.data?.error || 'Failed to resend verification email'
            }
        };
    }
};


export const changePassword = async (oldPassword, newPassword) => {
    try {
        const data = {
            oldPassword,
            newPassword
        };
        const response = await axios.post(`${CONNECTION}://${SERVER_IP}/${ROUTE}/change_password`, data, { withCredentials: true });
        return response;
    } catch (error) {
        console.error('Error changing password', error);
        throw error;
    }
};

export const recoverPassword = async (email) => {
    try {
        const response = await axios.post(
            `${CONNECTION}://${SERVER_IP}/${ROUTE}/recover-password`,
            { email },
            { withCredentials: true }
        );
        return {
            success: true,
            status: response.status,
            data: response.data,
            error: null
        };
    } catch (error) {
        return {
            success: false,
            status: error.response?.status || 500,
            data: null,
            error: {
                details: error.response?.data?.details || error.response?.data?.error || 'Failed to send recovery email'
            }
        };
    }
};
