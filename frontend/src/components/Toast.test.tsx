
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ToastContainer } from './Toast';
describe('Toast', () => {
  it('renders error toast', () => { render(<ToastContainer toasts={[{id:'1',kind:'error',message:'oops'}]} onDismiss={()=>{}} />); expect(screen.getByText('oops')).toBeInTheDocument(); });
  it('renders empty when none', () => { const { container } = render(<ToastContainer toasts={[]} onDismiss={()=>{}} />); expect(container.firstChild).toBeNull(); });
});
