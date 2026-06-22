'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './AppNav.module.css';

const LINKS = [
  { href: '/', label: 'Dashboard' },
  { href: '/ai', label: 'AI Study' },
];

export default function AppNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      <div className={styles.brand}>QUANT</div>
      <div className={styles.links}>
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`${styles.link} ${pathname === link.href ? styles.active : ''}`}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
