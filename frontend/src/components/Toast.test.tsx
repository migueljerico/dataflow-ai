
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ToastContainer } from './Toast';
import { LanguageProvider } from '../context/LanguageContext';
describe('Toast', () => {
  it('renders error toast', () => { render(<LanguageProvider><ToastContainer toasts={[{id:'1',kind:'error',message:'oops'}]} onDismiss={()=>{}} /></LanguageProvider>); expect(screen.getByText('oops')).toBeInTheDocument(); });
  it('renders empty when none', () => { const { container } = render(<LanguageProvider><ToastContainer toasts={[]} onDismiss={()=>{}} /></LanguageProvider>); expect(container.firstChild).toBeNull(); });
});
