/**
 * Unit tests for useFeatureFlag hook with percentage rollout
 */

import { describe, it, expect } from 'vitest';
import { hashToBucket, isUserInRollout } from '../useFeatureFlag';

describe('hashToBucket', () => {
  it('should return deterministic values between 0-99', () => {
    const userId = 'user@example.com';
    const bucket1 = hashToBucket(userId);
    const bucket2 = hashToBucket(userId);

    expect(bucket1).toBe(bucket2); // Deterministic
    expect(bucket1).toBeGreaterThanOrEqual(0);
    expect(bucket1).toBeLessThan(100);
  });

  it('should distribute different users across buckets', () => {
    const buckets = new Set<number>();

    for (let i = 0; i < 100; i++) {
      const userId = `user${i}@example.com`;
      const bucket = hashToBucket(userId);
      buckets.add(bucket);
    }

    // With 100 users, we should see multiple different buckets
    expect(buckets.size).toBeGreaterThan(10);
  });

  it('should handle same email consistently', () => {
    const email = 'test.user@company.com';
    const results = new Set<number>();

    // Hash same email 10 times
    for (let i = 0; i < 10; i++) {
      results.add(hashToBucket(email));
    }

    // Should always return same bucket
    expect(results.size).toBe(1);
  });
});

describe('isUserInRollout', () => {
  it('should include all users at 100% rollout', () => {
    const users = [
      'user1@example.com',
      'user2@example.com',
      'user3@example.com',
      'admin@company.com',
      'test@test.com',
    ];

    users.forEach(userId => {
      expect(isUserInRollout(userId, 100)).toBe(true);
    });
  });

  it('should exclude all users at 0% rollout', () => {
    const users = [
      'user1@example.com',
      'user2@example.com',
      'user3@example.com',
    ];

    users.forEach(userId => {
      expect(isUserInRollout(userId, 0)).toBe(false);
    });
  });

  it('should include approximately correct percentage of users', () => {
    const percentage = 10;
    const totalUsers = 1000;
    let includedCount = 0;

    for (let i = 0; i < totalUsers; i++) {
      const userId = `user${i}@example.com`;
      if (isUserInRollout(userId, percentage)) {
        includedCount++;
      }
    }

    // Allow 3% variance (e.g., 7-13% for 10% target)
    const expectedMin = (percentage - 3) * totalUsers / 100;
    const expectedMax = (percentage + 3) * totalUsers / 100;

    expect(includedCount).toBeGreaterThanOrEqual(expectedMin);
    expect(includedCount).toBeLessThanOrEqual(expectedMax);
  });

  it('should maintain consistency for same user', () => {
    const userId = 'consistent@example.com';
    const result1 = isUserInRollout(userId, 25);
    const result2 = isUserInRollout(userId, 25);
    const result3 = isUserInRollout(userId, 25);

    expect(result1).toBe(result2);
    expect(result2).toBe(result3);
  });

  it('should include 10% users in 25% rollout (gradual increase)', () => {
    // If user is in 10% rollout, they should also be in 25% rollout
    const userId = 'test@example.com';

    if (isUserInRollout(userId, 10)) {
      expect(isUserInRollout(userId, 25)).toBe(true);
      expect(isUserInRollout(userId, 50)).toBe(true);
      expect(isUserInRollout(userId, 100)).toBe(true);
    }
  });
});

describe('Rollout scenarios', () => {
  it('should support gradual rollout: 10% → 25% → 50% → 100%', () => {
    const testUsers = [
      'alice@company.com',
      'bob@company.com',
      'charlie@company.com',
      'diana@company.com',
    ];

    // Track which users are included at each percentage
    const rollout10 = testUsers.filter(u => isUserInRollout(u, 10));
    const rollout25 = testUsers.filter(u => isUserInRollout(u, 25));
    const rollout50 = testUsers.filter(u => isUserInRollout(u, 50));
    const rollout100 = testUsers.filter(u => isUserInRollout(u, 100));

    // All users in 10% should be in 25%
    rollout10.forEach(user => {
      expect(rollout25).toContain(user);
    });

    // All users in 25% should be in 50%
    rollout25.forEach(user => {
      expect(rollout50).toContain(user);
    });

    // All users in 50% should be in 100%
    rollout50.forEach(user => {
      expect(rollout100).toContain(user);
    });

    // 100% should include everyone
    expect(rollout100.length).toBe(testUsers.length);
  });

  it('should handle edge case percentages', () => {
    const userId = 'edge@example.com';

    expect(isUserInRollout(userId, -5)).toBe(false); // Negative -> 0%
    expect(isUserInRollout(userId, 105)).toBe(true); // Over 100% -> 100%
  });
});
