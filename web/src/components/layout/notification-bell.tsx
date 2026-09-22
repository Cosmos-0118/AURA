'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuraStore } from '@/lib/demo/store';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';

export function NotificationBell() {
  const store = useAuraStore();
  const [hasUnread, setHasUnread] = useState(true);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant='ghost'
            size='icon'
            aria-label='Agent activity notifications'
            className='relative size-8'
            onClick={() => setHasUnread(false)}
          />
        }
      >
        <Icons.notification className='size-4' />
        {hasUnread && (
          <span className='absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive animate-pulse' />
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent className='w-80 p-2' align='end'>
        <DropdownMenuLabel className='text-xs font-bold flex items-center justify-between pb-2'>
          <span>Agent Activity Alerts</span>
          <span className='text-[10px] text-muted-foreground font-normal'>
            {store.activity.length} updates
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className='flex flex-col gap-2 max-h-72 overflow-y-auto py-1'>
          {store.activity.slice(0, 5).map((act) => (
            <div
              key={act.id}
              className='flex items-start gap-2.5 p-2 rounded-md hover:bg-muted/40 text-xs transition-colors'
            >
              <div className='rounded-full p-1 bg-primary/10 text-primary mt-0.5 shrink-0'>
                <Icons.sparkles className='size-3' />
              </div>
              <div className='flex flex-col flex-1 min-w-0'>
                <div className='flex items-center justify-between'>
                  <span className='font-bold text-foreground text-[11px]'>{act.agent}</span>
                  <span className='text-[10px] text-muted-foreground'>{act.time}</span>
                </div>
                <p className='text-[11px] text-muted-foreground line-clamp-2 mt-0.5 leading-snug'>
                  {act.description}
                </p>
              </div>
            </div>
          ))}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link href='/dashboard' aria-label='View Command Center' className='w-full text-center text-xs font-semibold text-primary' />}>
          View Command Center
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
