import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmStoreListComponent } from './algorithm-store-list.component';

describe('AlgorithmStoreListComponent', () => {
  let component: AlgorithmStoreListComponent;
  let fixture: ComponentFixture<AlgorithmStoreListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmStoreListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmStoreListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
