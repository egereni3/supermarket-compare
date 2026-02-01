import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgForOf, NgIf } from '@angular/common';
import { Search, SearchResultPayload, ItemRow } from '../../services/search';
import { Basket } from '../../services/basket';
import { Auth } from '../../auth/auth';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [NgForOf, NgIf],
  templateUrl: './results.html',
  styleUrls: ['./results.scss'],
})
export class Results implements OnInit {
  query = '';
  results: SearchResultPayload['results'] | null = null; 
  loading = false;
  animatingKeys = new Set<string>();

  constructor(
    private route: ActivatedRoute,
    private search: Search,
    private basket: Basket,
    private auth: Auth,
    private router: Router,
  ) {}

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/home']);
      return;
    }
    this.route.queryParams.subscribe(params => {
      const q = params['q'] ?? '';
      this.query = q;

      const cached = this.search.getLastResult();
      if (cached && cached.query === q) {
        this.results = cached.results; 
        return;
      }

      if (q) {
        this.loading = true;
        this.search.search(q).subscribe({
          next: (resp: SearchResultPayload) => {  
            this.loading = false;
            this.results = resp.results; 
          },
          error: () => {
            this.loading = false;
          },
        });
      }
    });
  }

  addToBasket(item: ItemRow, market: string): void {  
    const [title, priceStr] = item;
    
    // Parse price
    let unitPrice = 0;
    const normalized = priceStr.trim().toLowerCase();
    
    if (normalized.endsWith('p')) {
      // Handle pence
      const pence = parseFloat(normalized.replace(/[^0-9.]/g, ''));
      unitPrice = pence / 100;
    } else {
      // Handle pounds
      unitPrice = parseFloat(normalized.replace(/[^0-9.]/g, '')) || 0;
    }
    
    this.basket.add({ title, unitPrice, market });
  }

  getItemKey(item: ItemRow, market: string, index: number): string {
    return `${market}:${item[0]}:${index}`;
  }

  onAddClick(item: ItemRow, market: string, index: number): void {
    const key = this.getItemKey(item, market, index);

    const triggerAnimation = () => {
      this.animatingKeys.add(key);
      // add item to basket
      this.addToBasket(item, market);
      setTimeout(() => this.animatingKeys.delete(key), 600);
    };

    // If already animating, restart animation so repeated clicks retrigger it
    if (this.animatingKeys.has(key)) {
      this.animatingKeys.delete(key);
      // small delay to ensure class removal is applied before re-adding
      setTimeout(triggerAnimation, 20);
    } else {
      triggerAnimation();
    }
  }

  isAnimating(item: ItemRow, market: string, index: number): boolean {
    return this.animatingKeys.has(this.getItemKey(item, market, index));
  }
}