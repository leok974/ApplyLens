import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Opportunities from './Opportunities';

// Mock the API modules
vi.mock('../api/opportunities', () => ({
  getOpportunities: vi.fn(),
  listOpportunities: vi.fn(),
  getOpportunityDetail: vi.fn(),
  runRoleMatch: vi.fn(),
  getCurrentResume: vi.fn(),
}));

vi.mock('../api/agent', () => ({
  getRoleMatch: vi.fn(),
}));

import * as opportunitiesApi from '../api/opportunities';
import * as agentApi from '../api/agent';

const mockOpportunities = [
  {
    id: 1,
    owner_email: 'test@applylens.com',
    source: 'linkedin',
    title: 'Senior Software Engineer',
    company: 'TechCorp',
    location: 'San Francisco, CA',
    remote_flag: true,
    salary_text: '$150k - $200k',
    level: 'Senior',
    tech_stack: ['Python', 'React', 'PostgreSQL'],
    apply_url: 'https://linkedin.com/jobs/123',
    posted_at: '2025-11-20T10:00:00Z',
    created_at: '2025-11-24T12:00:00Z',
    match_bucket: 'strong',
    match_score: 0.85,
  },
  {
    id: 2,
    owner_email: 'test@applylens.com',
    source: 'indeed',
    title: 'Full Stack Developer',
    company: 'StartupXYZ',
    location: 'Remote',
    remote_flag: true,
    salary_text: '$120k - $160k',
    level: 'Mid',
    tech_stack: ['JavaScript', 'Node.js', 'MongoDB'],
    apply_url: 'https://indeed.com/jobs/456',
    posted_at: '2025-11-22T14:30:00Z',
    created_at: '2025-11-24T13:00:00Z',
    match_bucket: 'possible',
    match_score: 0.65,
  },
];

const mockRoleMatchResponse = {
  bucket: 'strong',
  score: 0.85,
  reasons: ['Strong Python experience', 'React skills match'],
  missing_skills: ['Kubernetes'],
  resume_tweaks: ['Highlight distributed systems experience'],
};

describe('OpportunitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders opportunities list', async () => {
    // Mock API responses
    vi.mocked(opportunitiesApi.listOpportunities).mockResolvedValue(mockOpportunities);

    render(
      <BrowserRouter>
        <Opportunities />
      </BrowserRouter>
    );

    // Wait for opportunities to load
    await waitFor(() => {
      expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument();
    });

    // Verify both opportunities are rendered
    expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument();
    expect(screen.getByText('Full Stack Developer')).toBeInTheDocument();
    expect(screen.getByText('TechCorp')).toBeInTheDocument();
    expect(screen.getByText('StartupXYZ')).toBeInTheDocument();
  });

  it('renders detail panel when opportunity is selected', async () => {
    vi.mocked(opportunitiesApi.listOpportunities).mockResolvedValue(mockOpportunities);
    vi.mocked(opportunitiesApi.getOpportunityDetail).mockResolvedValue({
      ...mockOpportunities[0],
      description: 'Full job description here',
      requirements: ['5+ years Python', 'React experience'],
    });

    render(
      <BrowserRouter>
        <Opportunities />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument();
    });

    // Click first opportunity
    const firstOpportunity = screen.getByText('Senior Software Engineer');
    firstOpportunity.click();

    // Wait for detail panel to render
    await waitFor(() => {
      expect(screen.getByText('TechCorp')).toBeInTheDocument();
    });

    // Verify detail content
    expect(screen.getByText(/San Francisco, CA/i)).toBeInTheDocument();
    expect(screen.getByText(/\$150k - \$200k/i)).toBeInTheDocument();
  });

  it('shows role match analysis when clicked', async () => {
    vi.mocked(opportunitiesApi.listOpportunities).mockResolvedValue(mockOpportunities);
    vi.mocked(agentApi.getRoleMatch).mockResolvedValue(mockRoleMatchResponse);

    render(
      <BrowserRouter>
        <Opportunities />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument();
    });

    // Click first opportunity to select it
    const firstOpportunity = screen.getByText('Senior Software Engineer');
    firstOpportunity.click();

    await waitFor(() => {
      // Look for "Analyze Match" button or similar
      const analyzeButton = screen.queryByText(/analyze/i);
      if (analyzeButton) {
        analyzeButton.click();
      }
    });

    // Verify role match was called
    await waitFor(() => {
      expect(opportunitiesApi.runRoleMatch).toHaveBeenCalled();
    });
  });

  it('handles empty opportunities list', async () => {
    vi.mocked(opportunitiesApi.listOpportunities).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <Opportunities />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no opportunities/i)).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    vi.mocked(opportunitiesApi.listOpportunities).mockRejectedValue(
      new Error('Failed to fetch opportunities')
    );

    render(
      <BrowserRouter>
        <Opportunities />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
