'use client';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem
} from '@/components/ui/sidebar';
import { navGroups } from '@/config/nav-config';
import { useFilteredNavGroups } from '@/hooks/use-nav';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icons } from '@/components/icons';

export default function AppSidebar() {
  const pathname = usePathname();
  const filteredGroups = useFilteredNavGroups(navGroups);

  return (
    <Sidebar collapsible='icon' expandOnHover>
      <SidebarHeader className='h-14 justify-center border-b px-4 group-data-[collapsible=icon]:px-2'>
        <div className='flex items-center gap-3'>
          <div className='flex size-8 shrink-0 items-center justify-center rounded-md bg-foreground text-background font-bold tracking-tight text-sm shadow-sm'>
            A
          </div>
          <div className='flex min-w-0 flex-col group-data-[collapsible=icon]:hidden'>
            <div className='flex items-center gap-1.5'>
              <span className='font-bold text-sm tracking-wide text-foreground'>AURA</span>
              <span className='rounded bg-emerald-500/10 px-1 py-0.5 text-[9px] font-semibold text-emerald-600 dark:text-emerald-400'>
                OPS DESK
              </span>
            </div>
            <span className='text-[10px] text-muted-foreground truncate'>
              AI Marketing Operations
            </span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent className='overflow-x-hidden'>
        {filteredGroups.map((group) => (
          <SidebarGroup key={group.label || 'ungrouped'} className='py-1'>
            {group.label && <SidebarGroupLabel className='text-[10px] tracking-wider text-muted-foreground/80 font-semibold'>{group.label}</SidebarGroupLabel>}
            <SidebarMenu>
              {group.items.map((item) => {
                const Icon = item.icon ? Icons[item.icon] : Icons.logo;
                return item?.items && item?.items?.length > 0 ? (
                  <Collapsible
                    key={item.title}
                    defaultOpen={item.isActive}
                    render={<SidebarMenuItem />}
                  >
                    <CollapsibleTrigger
                      render={
                        <SidebarMenuButton
                          tooltip={item.title}
                          isActive={pathname === item.url}
                          className='group/collapsible'
                        />
                      }
                    >
                      {item.icon && <Icon className='size-4' />}
                      <span className='text-sm'>{item.title}</span>
                      {item.label && (
                        <span className='ml-auto mr-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary'>
                          {item.label}
                        </span>
                      )}
                      <Icons.chevronRight className='ml-auto transition-transform duration-200 group-data-panel-open/collapsible:rotate-90' />
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {item.items?.map((subItem) => (
                          <SidebarMenuSubItem key={subItem.title}>
                            <SidebarMenuSubButton
                              render={<Link href={subItem.url} aria-label={subItem.title} />}
                              isActive={pathname === subItem.url}
                            >
                              <span>{subItem.title}</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </Collapsible>
                ) : (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      render={<Link href={item.url} aria-label={item.title} />}
                      tooltip={item.title}
                      isActive={pathname === item.url}
                    >
                      <Icon className='size-4' />
                      <span className='text-sm'>{item.title}</span>
                      {item.label && (
                        <span className='ml-auto rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary'>
                          {item.label}
                        </span>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className='p-2 border-t'>
        <div className='flex items-center gap-2 px-2 py-1.5 rounded-md bg-muted/40 text-[11px] text-muted-foreground font-medium group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0'>
          <span className='size-2 rounded-full bg-emerald-500 shrink-0' />
          <span className='truncate text-foreground font-semibold group-data-[collapsible=icon]:hidden'>JA Assure Desk</span>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
