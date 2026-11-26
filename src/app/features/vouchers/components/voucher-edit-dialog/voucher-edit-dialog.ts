import { ChangeDetectionStrategy, Component, computed, effect, input, model, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { DemoVoucher, VoucherDraft, VoucherIssuerType } from '../../vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, FormsModule, SelectModule],
  selector: 'app-voucher-edit-dialog',
  templateUrl: './voucher-edit-dialog.html',
})
export class VoucherEditDialog {
  readonly visible = model(false);
  readonly voucher = input<DemoVoucher | null>(null);

  readonly saved = output<VoucherDraft>();

  protected readonly issuer = signal('');
  protected readonly issuerType = signal<VoucherIssuerType>('INSTITUTION');
  protected readonly issuerTypes = [{ value: 'INSTITUTION', label: 'Institución' }, { value: 'STATION', label: 'Estación' }];
  protected readonly error = signal('');

  /** Solo se puede guardar cuando el emisor o su tipo difieren del vale original. */
  protected readonly dirty = computed(() => {
    const voucher = this.voucher();
    return (
      this.issuer() !== (voucher?.issuer ?? '') ||
      this.issuerType() !== (voucher?.issuerType ?? 'INSTITUTION')
    );
  });

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
