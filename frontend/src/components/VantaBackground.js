import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import VANTA from 'vanta/dist/vanta.net.min';

const VantaBackground = ({ children, options = {} }) => {
  const vantaRef = useRef(null);
  const vantaEffect = useRef(null);

  useEffect(() => {
    if (!vantaEffect.current) {
      vantaEffect.current = VANTA({
        el: vantaRef.current,
        THREE: THREE,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        ...options, // ONLY use passed options
      });
    }

    return () => {
      if (vantaEffect.current) {
        vantaEffect.current.destroy();
        vantaEffect.current = null;
      }
    };
  }, [options]); // Add options to dependency array

  return (
    <div ref={vantaRef} style={{ width: '100%', height: '100vh' }}>
      {children}
    </div>
  );
};

export default VantaBackground;
