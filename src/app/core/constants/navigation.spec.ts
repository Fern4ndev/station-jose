import { describe, expect, it } from 'vitest';
import { routes } from '../../app.routes';
import { NAVIGATION } from './navigation';

describe('navigation permissions', () => {
  it('matches every menu entry to its route permission', () => {
    const children = routes.find((route) => route.path === '' && route.children)?.children ?? [];
    for (const item of NAVIGATION.flatMap((group) => group.items)) {
      const route = children.find((candidate) => candidate.path === item.path.slice('/'.length));
      expect(route?.data?.['permission'], item.path).toBe(item.permission);
    }
  });
});
