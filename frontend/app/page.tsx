import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function Home() {
  const cookieStore = await cookies();
  const hasAuthToken =
    Boolean(cookieStore.get('access_token')?.value) ||
    Boolean(cookieStore.get('refresh_token')?.value);

  redirect(hasAuthToken ? '/debates' : '/login');
}
