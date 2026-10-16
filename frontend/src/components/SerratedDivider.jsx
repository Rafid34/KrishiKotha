import React from 'react';

/**
 * SerratedDivider — procedural jagged edge divider using radial-gradient mask.
 * Purely decorative, aria-hidden. Placed between sections.
 */
export default function SerratedDivider({ className = '', style = {} }) {
  return (
    <div
      className={`serrated-divider ${className}`}
      style={style}
      aria-hidden="true"
      role="presentation"
    />
  );
}
