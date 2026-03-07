import React from 'react';
import {render, fireEvent} from '@testing-library/react-native';
import InsightCard from '../src/components/InsightCard';
import {Insight} from '../src/types';

jest.mock('react-native-video', () => 'Video');

const mockInsight: Insight = {
  id: 1,
  insight_text: 'Product-market fit is not a moment, it is a spectrum',
  category: 'takeaway',
  start_timestamp: 120.0,
  end_timestamp: 155.0,
  clip_url: null,
  order: 0,
};

describe('InsightCard', () => {
  it('renders insight text', () => {
    const {getByText} = render(<InsightCard insight={mockInsight} />);
    expect(
      getByText('Product-market fit is not a moment, it is a spectrum'),
    ).toBeTruthy();
  });

  it('renders category badge', () => {
    const {getByText} = render(<InsightCard insight={mockInsight} />);
    expect(getByText('Key Takeaway')).toBeTruthy();
  });

  it('renders formatted timestamps', () => {
    const {getByText} = render(<InsightCard insight={mockInsight} />);
    expect(getByText('2:00 - 2:35')).toBeTruthy();
  });

  it('shows placeholder when no clip url', () => {
    const {getByText} = render(<InsightCard insight={mockInsight} />);
    expect(getByText('Clip generating...')).toBeTruthy();
  });

  it('calls onShare when share button pressed', () => {
    const onShare = jest.fn();
    const {getByText} = render(
      <InsightCard insight={mockInsight} onShare={onShare} />,
    );

    fireEvent.press(getByText('Share'));
    expect(onShare).toHaveBeenCalledWith(mockInsight);
  });
});
