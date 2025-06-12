import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CommunityStoreComponent } from './community-store.component';

describe('CommunityStoreComponent', () => {
  let component: CommunityStoreComponent;
  let fixture: ComponentFixture<CommunityStoreComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [CommunityStoreComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommunityStoreComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
