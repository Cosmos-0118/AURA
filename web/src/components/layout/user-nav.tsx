'use client';

import React from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import Link from 'next/link';

export function UserNav() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant='ghost' aria-label='User profile menu' className='relative h-8 w-8 rounded-full' />}>
        <Avatar className='h-8 w-8'>
          <AvatarFallback className='bg-primary/10 text-primary font-bold text-xs'>
            MC
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent className='w-56' align='end'>
        <DropdownMenuGroup>
          <DropdownMenuLabel className='font-normal'>
            <div className='flex flex-col space-y-1'>
              <p className='text-xs font-bold leading-none text-foreground'>Marcus Chen</p>
              <p className='text-[10px] leading-none text-muted-foreground'>
                Head of Operations · JA Assure
              </p>
            </div>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem render={<Link href='/dashboard/studio' aria-label='Campaign Studio' />}>
            Campaign Studio
          </DropdownMenuItem>
          <DropdownMenuItem render={<Link href='/dashboard/review' aria-label='Review Queue' />}>
            Review Queue
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
