import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreUserReadComponent } from './store-user-read.component';

describe('StoreUserReadComponent', () => {
  let component: StoreUserReadComponent;
  let fixture: ComponentFixture<StoreUserReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreUserReadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreUserReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
