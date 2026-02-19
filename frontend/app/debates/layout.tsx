'use client';

import Header from '@/components/Header';

export default function DebatesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header />
      <main className="debates-main">{children}</main>
    </>
  );
}
