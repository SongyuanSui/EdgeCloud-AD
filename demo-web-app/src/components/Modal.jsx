import React from 'react';
import './Modal.css'; 

const Modal = ({ show, onClose, blackBackground = true, children }) => {
  if (!show) {
    return null; 
  }

  return (
    <div 
      className={`modal ${blackBackground ? 'modal-black' : ''}`} 
      onClick={onClose}
    >
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {/* <span className="close" onClick={onClose}>&times;</span> */}
        <button className="close-button" onClick={onClose}>
          &times;
        </button>
        <div>{children}</div>
      </div>
    </div>
  );
};

export default Modal;