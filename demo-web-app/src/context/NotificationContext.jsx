import React, { createContext, useContext, useState, useCallback } from 'react';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
  const [notification, setNotification] = useState({
    message: '',
    type: '', // 'success', 'error', 'warning'
    isVisible: false,
    isFading: false,
  });

  const showNotification = useCallback((message, type = 'success', duration = 2000) => {
    setNotification({
      message,
      type,
      isVisible: true,
      isFading: false,
    });

    setTimeout(() => {
      setNotification(prev => ({
        ...prev,
        isFading: true,
      }));
      
      setTimeout(() => {
        setNotification(prev => ({
          ...prev,
          isVisible: false,
        }));
      }, 300); 
    }, duration - 300);  // Subtract animation duration from total duration
  }, []);

  return (
    <NotificationContext.Provider value={{ notification, showNotification }}>
      {children}
      {notification.isVisible && (
        <div className={`notification ${notification.type} ${notification.isFading ? 'fade-out' : ''}`}>
          {notification.message}
        </div>
      )}
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context.showNotification;
}; 