import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddAlgoStoreComponent } from './add-algo-store.component';

describe('AddAlgoStoreComponent', () => {
  let component: AddAlgoStoreComponent;
  let fixture: ComponentFixture<AddAlgoStoreComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AddAlgoStoreComponent]
    });
    fixture = TestBed.createComponent(AddAlgoStoreComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
