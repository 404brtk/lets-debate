'use client';

import { useEffect } from 'react';
import Header from '@/components/Header';
import { useAuth } from '@/store/auth';

export default function DebatesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, user, fetchUser } = useAuth();

  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchUser();
    }
  }, [isAuthenticated, user, fetchUser]);

  return (
    <>
      <Header />
      <main className="debates-main">{children}</main>
    </>
  );
}
