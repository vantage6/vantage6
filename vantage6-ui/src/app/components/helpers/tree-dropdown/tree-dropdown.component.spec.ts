import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TreeDropdownComponent } from './tree-dropdown.component';

describe('TreeDropdownComponent', () => {
  let component: TreeDropdownComponent;
  let fixture: ComponentFixture<TreeDropdownComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TreeDropdownComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TreeDropdownComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
