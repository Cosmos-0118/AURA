'use client';

import React from 'react';
import { SidebarTrigger } from '../ui/sidebar';
import { Separator } from '../ui/separator';
import { Breadcrumbs } from '../breadcrumbs';
import SearchInput from '../search-input';
import { ThemeModeToggle } from '../themes/theme-mode-toggle';
import { NotificationBell } from './notification-bell';
import { UserNav } from './user-nav';

export default function Header() {
  return (
    <header className='bg-background/80 sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-2 border-b backdrop-blur-md px-4 sm:px-6 lg:px-8 xl:px-12'>
      <div className='flex min-w-0 items-center gap-2'>
        <SidebarTrigger className='-ml-1 md:hidden' />
        <Breadcrumbs />
      </div>

      <div className='flex items-center gap-2.5'>
        <div className='hidden md:flex'>
          <SearchInput />
        </div>
        <NotificationBell />
        <ThemeModeToggle />
        <Separator orientation='vertical' className='h-4 mx-1 hidden sm:block' />
        <UserNav />
      </div>
    </header>
  );
}

