import { ChangeDetectionStrategy, Component, effect, input, model, output, signal } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { DemoVoucher, VoucherDraft, VoucherIssuerType } from '../../vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-voucher-edit-dialog',
  templateUrl: './voucher-edit-dialog.html',
})
export class VoucherEditDialog {
  readonly visible = model(false);
  readonly voucher = input<DemoVoucher | null>(null);

  readonly saved = output<VoucherDraft>();

  protected readonly issuer = signal('');
  protected readonly issuerType = signal<VoucherIssuerType>('INSTITUTION');
  protected readonly error = signal('');

  constructor() {
    effect(() => {
      if (!this.visible()) {
        return;
      }
      const voucher = this.voucher();
      this.issuer.set(voucher?.issuer ?? '');
      this.issuerType.set(voucher?.issuerType ?? 'INSTITUTION');
      this.error.set('');
    });
  }

  protected setIssuer(event: Event): void {
    this.issuer.set((event.target as HTMLInputElement).value);
  }

  protected setIssuerType(event: Event): void {
    this.issuerType.set((event.target as HTMLSelectElement).value as VoucherIssuerType);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const voucher = this.voucher();
    const issuer = this.issuer().trim();
    if (!voucher) {
      return;
    }
    if (!issuer) {
      this.error.set('Indica el nombre del emisor.');
      return;
    }
    this.saved.emit({ id: voucher.id, issuer, issuerType: this.issuerType() });
    this.visible.set(false);
  }
}
