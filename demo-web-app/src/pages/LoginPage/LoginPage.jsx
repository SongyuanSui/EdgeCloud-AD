import { TbEye, TbEyeClosed } from "react-icons/tb";
import React, { useEffect, useState } from 'react';
import './LoginPage.css';
import { useNavigate } from 'react-router-dom';
import { login, checkLogin } from '../../api/auth_api';
import { useNotification } from '../../context/NotificationContext';

export const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const showNotification = useNotification();
    const [showPassword, setShowPassword] = useState(false);

    const handleLogin = () => {
        setError('');
        if (!username || !password) {
            setError('Username and password cannot be empty.');
            return;
        }
        login(username, password)
            .then((response) => {
                if (response.status === 200) {
                    showNotification('Login successful!', 'success');
                    navigate('/main');
                } else {
                    setError('Login failed. Please try again.');
                }
            })
            .catch((error) => {
                if (error.response && error.response.status === 401) {
                    setError('Invalid username or password.');
                } else {
                    setError('An error occurred. Please try again later.');
                }
            }); 
    };

    const handleRegisterRedirect = () => {
        navigate('/register');
    };

    const handleRecoverPasswordRedirect = () => {
        navigate('/recover-password');
    };


    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const recoverStatusParam = urlParams.get("recover_status");

        if (recoverStatusParam === 'confirmed') {
            showNotification("Your password has been reset. Please log in with your new password.", "success");
        } else if (recoverStatusParam === 'expired') {
            showNotification("Your recovery link is expired. Please initiate a new password recovery.", "error");
        } else if (recoverStatusParam === 'invalid') {
            showNotification("Your recovery link is invalid. Please try again.", "error");
        }
        window.history.replaceState({}, '', '/login');
    }, []);

    useEffect(() => {
        checkLogin()
            .then((response) => {
                if (response.status === 200) {
                    navigate('/main');
                }
            })
            .catch((error) => {
                console.log("Status:", error);
            });
    }, [navigate]);

    const togglePasswordVisibility = () => {
        setShowPassword((prevState) => !prevState);
    };

    return (
        <div className="login-container">
            <div className="login-box">
                <h1 className="login-title">Welcome Back</h1>
                <input
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="login-input"
                />
                <div className="password-input-wrapper">
                    <input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="password-input"
                    />
                    <div className="eye-icon-container" onClick={togglePasswordVisibility}>
                        <button type="button" className="eye-icon-button">
                            {showPassword ? <TbEyeClosed size={20} /> : <TbEye size={20} />}
                        </button>
                    </div>
                </div>
                <p className="recovery-text">
                    <span onClick={handleRecoverPasswordRedirect} className="recovery-link">
                        Forget Password
                    </span>
                </p>

                {error && <div className="login-error">{error}</div>}
                <button onClick={handleLogin} className="login-button">
                    Login
                </button>
                
                <p className="register-text">
                    No account?{' '}
                    <span onClick={handleRegisterRedirect} className="register-link">
                        Register here
                    </span>
                </p>
            </div>
        </div>
    );
};
