import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { checkLogin } from '../api/auth_api';

const AuthWrapper = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const publicPages = ['/login', '/register', '/verification-resend', '/verification-message', '/recover-password'];
    checkLogin()
      .then((response) => {
        if (response.status === 200) {
          if (publicPages.includes(location.pathname) || location.pathname === '/') {
            navigate('/main');
          }
        } 
        setLoading(false);
      })
      .catch((error) => {
        /** Muted original code
        if (location.pathname !== '/login' && location.pathname !== '/register') {
          navigate('/login');
        }
        */
        /** New code for verification-email-feature --> Allow public access */
        if (!publicPages.includes(location.pathname)) {
          navigate(`/login${location.search}`);
        }        
        setLoading(false);
      });
  }, [navigate, location]);

  if (loading) {
    return null;
  }

  return children;
};

export default AuthWrapper;
