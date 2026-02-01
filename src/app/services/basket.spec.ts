import { TestBed } from '@angular/core/testing';

import { Basket } from './basket';

describe('Basket', () => {
  let service: Basket;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Basket);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
