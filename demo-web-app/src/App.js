
import './App.css';
import { MainPage } from './pages/MainPage/MainPage';
import { NotificationProvider } from './context/NotificationContext'; 
import { LoginPage } from './pages/LoginPage/LoginPage';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AuthWrapper from './pages/AuthWrapper';

function App() {
  return (
    <div className="App">
      <NotificationProvider>
      <Router>
        <AuthWrapper>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/main" element={<MainPage />} />
          </Routes>
        </AuthWrapper>
        </Router>
      </NotificationProvider>
    </div>
  );
}

export default App;
