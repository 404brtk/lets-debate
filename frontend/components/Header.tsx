'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/store/auth';

export default function Header() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navLinks = [
    { href: '/debates', label: 'Debates' },
    { href: '/profile', label: 'Profile' },
  ];

  return (
    <header className="header">
      <div className="header-inner">
        <Link href="/debates" className="header-logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">Let&apos;s Debate</span>
        </Link>

        <nav className="header-nav">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`nav-link ${pathname === link.href ? 'nav-link-active' : ''}`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          {user && (
            <span className="header-username">{user.username}</span>
          )}
          <button onClick={logout} className="btn btn-ghost btn-sm">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
